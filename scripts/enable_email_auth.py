from pathlib import Path
import sys

if len(sys.argv) != 3:
    raise SystemExit("Usage: enable_email_auth.py path/to/main.dart path/to/AndroidManifest.xml")

path = Path(sys.argv[1])
manifest = Path(sys.argv[2])
if not path.is_file():
    raise SystemExit(f"Passenger app entrypoint not found: {path}")
source = path.read_text(encoding="utf-8")
source = source.replace(
    "await Supabase.initialize(url: supabaseUrl, anonKey: supabasePublishableKey);",
    "await Supabase.initialize(url: supabaseUrl, publishableKey: supabasePublishableKey);",
)
source = source.replace("? const PhoneLoginScreen() : const BookingScreen(),", "? const EmailLoginScreen() : const BookingScreen(),")

start_marker = "class PhoneLoginScreen extends StatefulWidget {"
end_marker = "\\nclass BookingScreen extends StatefulWidget"
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
  bool sent = false, busy = false;
  String? error;

  Future<void> submit() async {
    final address = email.text.trim();
    if (address.isEmpty || !address.contains('@')) {
      setState(() => error = 'أدخل عنوان بريد إلكتروني صحيح.');
      return;
    }
    setState(() { busy = true; error = null; });
    try {
      await Supabase.instance.client.auth.signInWithOtp(
        email: address,
        emailRedirectTo: 'com.ridealgeria.mashwari://login-callback',
      );
      if (mounted) setState(() => sent = true);
    } on AuthException catch (e) {
      if (mounted) setState(() => error = e.message);
    } catch (_) {
      if (mounted) setState(() => error = 'تعذر إرسال رابط الدخول. تحقق من الاتصال وحاول مجدداً.');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  void changeEmail() {
    setState(() { sent = false; error = null; });
  }

  @override
  void dispose() { email.dispose(); super.dispose(); }

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
          Text(sent ? 'أرسلنا رابط الدخول إلى بريدك. افتحه لإكمال تسجيل الدخول.' : 'سجّل ببريدك الإلكتروني للمتابعة', textAlign: TextAlign.center),
          const SizedBox(height: 28),
          TextField(controller: email, enabled: !sent,
            keyboardType: TextInputType.emailAddress, textDirection: TextDirection.ltr,
            autofillHints: const [AutofillHints.email],
            decoration: const InputDecoration(labelText: 'البريد الإلكتروني', border: OutlineInputBorder(), prefixIcon: Icon(Icons.email_outlined))),
          if (sent) ...[
            const SizedBox(height: 12),
            TextButton(onPressed: busy ? null : changeEmail, child: const Text('تغيير البريد الإلكتروني')),
          ],
          if (error != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text(error!, textAlign: TextAlign.center, style: const TextStyle(color: Colors.red))),
          const SizedBox(height: 18),
          FilledButton(onPressed: busy ? null : submit,
            child: Text(busy ? 'يرجى الانتظار...' : sent ? 'إعادة إرسال رابط الدخول' : 'إرسال رابط الدخول إلى البريد')),
          const SizedBox(height: 14),
          const Text('افتح رسالة مشواري في بريدك واضغط رابط تسجيل الدخول. لن تحتاج إلى SMS.', textAlign: TextAlign.center,
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
if "emailRedirectTo:" not in source or "com.ridealgeria.mashwari://login-callback" not in source:
    raise SystemExit("Email magic-link implementation verification failed")
path.write_text(source, encoding="utf-8")

if not manifest.is_file():
    raise SystemExit(f"Generated Android manifest not found: {manifest}")
xml = manifest.read_text(encoding="utf-8")
intent = """
            <intent-filter>
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.BROWSABLE" />
                <data android:scheme="com.ridealgeria.mashwari" android:host="login-callback" />
            </intent-filter>
"""
if "com.ridealgeria.mashwari" not in xml:
    if "</activity>" not in xml:
        raise SystemExit("Generated Android manifest has no activity element")
    xml = xml.replace("</activity>", intent + "        </activity>", 1)
manifest.write_text(xml, encoding="utf-8")
print(f"Email magic-link login and Android deep link configured: {path}")
