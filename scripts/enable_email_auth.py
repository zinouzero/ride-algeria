from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("Usage: enable_email_auth.py path/to/passenger_app/lib/main.dart")

path = Path(sys.argv[1])
if not path.is_file():
    raise SystemExit(f"Passenger app entrypoint not found: {path}")
source = path.read_text(encoding="utf-8")

source = source.replace(
    "await Supabase.initialize(url: supabaseUrl, anonKey: supabasePublishableKey);",
    "await Supabase.initialize(url: supabaseUrl, publishableKey: supabasePublishableKey);",
)
source = source.replace(
    "? const PhoneLoginScreen() : const BookingScreen(),",
    "? const EmailLoginScreen() : const BookingScreen(),",
)

start_marker = "class PhoneLoginScreen extends StatefulWidget {"
end_marker = "\nclass BookingScreen extends StatefulWidget"
if start_marker in source:
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    email_screen = r"""class EmailLoginScreen extends StatefulWidget {
  const EmailLoginScreen({super.key});
  @override
  State<EmailLoginScreen> createState() => _EmailLoginScreenState();
}

class _EmailLoginScreenState extends State<EmailLoginScreen> {
  final email = TextEditingController();
  final code = TextEditingController();
  bool sent = false, busy = false;
  String? error;

  Future<void> submit() async {
    final address = email.text.trim();
    if (!sent && (address.isEmpty || !address.contains('@'))) {
      setState(() => error = 'أدخل عنوان بريد إلكتروني صحيح.');
      return;
    }
    if (sent && code.text.trim().length < 6) {
      setState(() => error = 'أدخل رمز التحقق المكوّن من 6 أرقام.');
      return;
    }
    setState(() { busy = true; error = null; });
    try {
      final auth = Supabase.instance.client.auth;
      if (!sent) {
        await auth.signInWithOtp(email: address);
        if (mounted) setState(() => sent = true);
      } else {
        await auth.verifyOTP(
          email: address,
          token: code.text.trim(),
          type: OtpType.email,
        );
      }
    } on AuthException catch (e) {
      if (mounted) setState(() => error = e.message);
    } catch (_) {
      if (mounted) setState(() => error = 'تعذر إكمال تسجيل الدخول. تحقق من الاتصال وحاول مجدداً.');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  void changeEmail() {
    setState(() { sent = false; code.clear(); error = null; });
  }

  @override
  void dispose() { email.dispose(); code.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) => Scaffold(
    body: SafeArea(child: Center(child: SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 460),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          const Icon(Icons.local_taxi_rounded, size: 64, color: Color(0xFF2457C5)),
          const SizedBox(height: 22),
          const Text('مرحبا بك في مشواري', textAlign: TextAlign.center,
            style: TextStyle(fontSize: 26, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Text(sent ? 'أدخل رمز التحقق الذي أرسلناه إلى بريدك الإلكتروني' : 'سجّل ببريدك الإلكتروني للمتابعة', textAlign: TextAlign.center),
          const SizedBox(height: 28),
          TextField(controller: email, enabled: !sent,
            keyboardType: TextInputType.emailAddress, textDirection: TextDirection.ltr,
            autofillHints: const [AutofillHints.email],
            decoration: const InputDecoration(labelText: 'البريد الإلكتروني', border: OutlineInputBorder(), prefixIcon: Icon(Icons.email_outlined))),
          if (sent) ...[
            const SizedBox(height: 12),
            TextField(controller: code, keyboardType: TextInputType.number,
              textDirection: TextDirection.ltr, maxLength: 6,
              autofillHints: const [AutofillHints.oneTimeCode],
              decoration: const InputDecoration(labelText: 'رمز التحقق (6 أرقام)', border: OutlineInputBorder(), prefixIcon: Icon(Icons.lock_outline))),
            Align(alignment: Alignment.centerLeft,
              child: TextButton(onPressed: busy ? null : changeEmail, child: const Text('تغيير البريد الإلكتروني'))),
          ],
          if (error != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text(error!, textAlign: TextAlign.center, style: const TextStyle(color: Colors.red))),
          const SizedBox(height: 18),
          FilledButton(onPressed: busy ? null : submit,
            child: Text(busy ? 'يرجى الانتظار...' : sent ? 'تأكيد الرمز' : 'إرسال رمز إلى البريد')),
          const SizedBox(height: 14),
          const Text('لن تحتاج إلى رقم هاتف أو رسائل SMS لتسجيل الدخول.', textAlign: TextAlign.center,
            style: TextStyle(fontSize: 12, color: Colors.black54)),
        ]),
      ),
    ))),
  );
}
"""
    source = source[:start] + email_screen + source[end:]
elif "class EmailLoginScreen extends StatefulWidget {" not in source:
    raise SystemExit("Could not find existing phone login screen to replace")

source = source.replace(
    "DropdownButtonFormField<String>(value:category,",
    "DropdownButtonFormField<String>(initialValue:category,",
)
if "const PhoneLoginScreen()" in source or "signInWithOtp(phone:" in source:
    raise SystemExit("Phone login references remain after patch")
if "signInWithOtp(email: address)" not in source or "OtpType.email" not in source:
    raise SystemExit("Email OTP implementation verification failed")

path.write_text(source, encoding="utf-8")
print(f"Email OTP login enabled in {path}")
