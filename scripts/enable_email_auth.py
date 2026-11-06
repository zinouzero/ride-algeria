from pathlib import Path
import re
import sys

if len(sys.argv) != 3:
    raise SystemExit('Usage: enable_email_auth.py path/to/main.dart path/to/AndroidManifest.xml')

source_path = Path(sys.argv[1])
manifest_path = Path(sys.argv[2])
if not source_path.is_file() or not manifest_path.is_file():
    raise SystemExit('Passenger Dart source or generated Android manifest is missing')
source = source_path.read_text(encoding='utf-8')
source = source.replace(
    'await Supabase.initialize(url: supabaseUrl, anonKey: supabasePublishableKey);',
    'await Supabase.initialize(url: supabaseUrl, publishableKey: supabasePublishableKey);',
)
source = re.sub(
    r'class AuthGate extends StatelessWidget \{.*?\n\}',
    '''class AuthGate extends StatelessWidget {
  const AuthGate({super.key});
  @override
  Widget build(BuildContext context) => StreamBuilder<AuthState>(
    stream: Supabase.instance.client.auth.onAuthStateChange,
    builder: (context, snapshot) {
      if (snapshot.data?.event == AuthChangeEvent.passwordRecovery) {
        return const PasswordRecoveryScreen();
      }
      return Supabase.instance.client.auth.currentSession == null
        ? const EmailPasswordAuthScreen() : const BookingScreen();
    },
  );
}''', source, count=1, flags=re.S)

start = source.find('class EmailLoginScreen extends StatefulWidget {')
if start < 0:
    start = source.find('class PhoneLoginScreen extends StatefulWidget {')
end = source.find('\nclass BookingScreen extends StatefulWidget', start)
if start < 0 or end < 0:
    raise SystemExit('Could not locate the existing login screen block')

screens = r'''class EmailPasswordAuthScreen extends StatefulWidget {
  const EmailPasswordAuthScreen({super.key});
  @override
  State<EmailPasswordAuthScreen> createState() => _EmailPasswordAuthScreenState();
}

class _EmailPasswordAuthScreenState extends State<EmailPasswordAuthScreen> {
  final email = TextEditingController();
  final password = TextEditingController();
  final confirmPassword = TextEditingController();
  bool registering = false, busy = false, hidePassword = true;
  String? error, notice;

  Future<void> submit() async {
    final address = email.text.trim();
    final pass = password.text;
    if (!address.contains('@') || address.length < 5) {
      setState(() => error = 'أدخل بريداً إلكترونياً صحيحاً.');
      return;
    }
    if (pass.length < 8) {
      setState(() => error = 'كلمة المرور لازم تكون 8 أحرف على الأقل.');
      return;
    }
    if (registering && pass != confirmPassword.text) {
      setState(() => error = 'تأكيد كلمة المرور غير مطابق.');
      return;
    }
    setState(() { busy = true; error = null; notice = null; });
    try {
      final auth = Supabase.instance.client.auth;
      if (registering) {
        final result = await auth.signUp(
          email: address,
          password: pass,
          emailRedirectTo: 'com.ridealgeria.mashwari://login-callback',
        );
        if (result.session == null && mounted) {
          setState(() => notice = 'تم إنشاء الحساب. افتح رسالة التأكيد مرة واحدة، وبعدها تدخل دائماً بالبريد وكلمة المرور.');
        }
      } else {
        await auth.signInWithPassword(email: address, password: pass);
      }
    } on AuthException catch (e) {
      if (mounted) setState(() => error = e.message);
    } catch (_) {
      if (mounted) setState(() => error = 'تعذر إكمال العملية. تحقق من الإنترنت وحاول مجدداً.');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> forgotPassword() async {
    final address = email.text.trim();
    if (!address.contains('@')) {
      setState(() => error = 'اكتب بريدك الإلكتروني أولاً لاسترجاع كلمة المرور.');
      return;
    }
    setState(() { busy = true; error = null; notice = null; });
    try {
      await Supabase.instance.client.auth.resetPasswordForEmail(
        address,
        redirectTo: 'com.ridealgeria.mashwari://login-callback',
      );
      if (mounted) setState(() => notice = 'أرسلنا رابط استرجاع كلمة المرور. استعمله مرة واحدة لاختيار كلمة مرور جديدة.');
    } on AuthException catch (e) {
      if (mounted) setState(() => error = e.message);
    } catch (_) {
      if (mounted) setState(() => error = 'تعذر إرسال رابط الاسترجاع. حاول لاحقاً.');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  void dispose() { email.dispose(); password.dispose(); confirmPassword.dispose(); super.dispose(); }

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
          Text(registering ? 'أنشئ حسابك مرة واحدة' : 'سجّل الدخول إلى حسابك', textAlign: TextAlign.center),
          const SizedBox(height: 26),
          TextField(controller: email, keyboardType: TextInputType.emailAddress,
            textDirection: TextDirection.ltr, autofillHints: const [AutofillHints.email],
            decoration: const InputDecoration(labelText: 'البريد الإلكتروني', border: OutlineInputBorder(), prefixIcon: Icon(Icons.email_outlined))),
          const SizedBox(height: 12),
          TextField(controller: password, obscureText: hidePassword,
            textDirection: TextDirection.ltr,
            autofillHints: [registering ? AutofillHints.newPassword : AutofillHints.password],
            decoration: InputDecoration(labelText: 'كلمة المرور', border: const OutlineInputBorder(), prefixIcon: const Icon(Icons.lock_outline),
              suffixIcon: IconButton(onPressed: () => setState(() => hidePassword = !hidePassword), icon: Icon(hidePassword ? Icons.visibility : Icons.visibility_off)))),
          if (registering) ...[
            const SizedBox(height: 12),
            TextField(controller: confirmPassword, obscureText: true, textDirection: TextDirection.ltr,
              decoration: const InputDecoration(labelText: 'تأكيد كلمة المرور', border: OutlineInputBorder(), prefixIcon: Icon(Icons.lock_reset))),
          ],
          if (!registering) Align(alignment: Alignment.centerLeft,
            child: TextButton(onPressed: busy ? null : forgotPassword, child: const Text('نسيت كلمة المرور؟'))),
          if (error != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text(error!, textAlign: TextAlign.center, style: const TextStyle(color: Colors.red))),
          if (notice != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text(notice!, textAlign: TextAlign.center, style: const TextStyle(color: Colors.green))),
          const SizedBox(height: 14),
          FilledButton(onPressed: busy ? null : submit,
            child: Text(busy ? 'يرجى الانتظار...' : registering ? 'إنشاء الحساب' : 'تسجيل الدخول')),
          const SizedBox(height: 8),
          TextButton(onPressed: busy ? null : () => setState(() { registering = !registering; error = null; notice = null; }),
            child: Text(registering ? 'عندي حساب بالفعل — تسجيل الدخول' : 'مستخدم جديد؟ إنشاء حساب')),
          const SizedBox(height: 10),
          const Text('يبقى حسابك محفوظاً على هذا الهاتف. لن تحتاج إلى رابط أو رسالة في كل مرة.', textAlign: TextAlign.center,
            style: TextStyle(fontSize: 12, color: Colors.black54)),
        ]),
      ),
    ))),
  );
}

class PasswordRecoveryScreen extends StatefulWidget {
  const PasswordRecoveryScreen({super.key});
  @override
  State<PasswordRecoveryScreen> createState() => _PasswordRecoveryScreenState();
}

class _PasswordRecoveryScreenState extends State<PasswordRecoveryScreen> {
  final password = TextEditingController();
  final confirm = TextEditingController();
  bool busy = false;
  String? error;
  Future<void> save() async {
    if (password.text.length < 8 || password.text != confirm.text) {
      setState(() => error = 'تأكد من تطابق كلمتي المرور وأنهما 8 أحرف على الأقل.');
      return;
    }
    setState(() { busy = true; error = null; });
    try {
      await Supabase.instance.client.auth.updateUser(UserAttributes(password: password.text));
    } on AuthException catch (e) {
      if (mounted) setState(() => error = e.message);
    } catch (_) {
      if (mounted) setState(() => error = 'تعذر تحديث كلمة المرور. حاول مجدداً.');
    } finally { if (mounted) setState(() => busy = false); }
  }
  @override
  void dispose() { password.dispose(); confirm.dispose(); super.dispose(); }
  @override
  Widget build(BuildContext context) => Scaffold(body: SafeArea(child: Center(child: SingleChildScrollView(
    padding: const EdgeInsets.all(24), child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      const Text('اختيار كلمة مرور جديدة', textAlign: TextAlign.center, style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
      const SizedBox(height: 24),
      TextField(controller: password, obscureText: true, decoration: const InputDecoration(labelText: 'كلمة المرور الجديدة', border: OutlineInputBorder())),
      const SizedBox(height: 12),
      TextField(controller: confirm, obscureText: true, decoration: const InputDecoration(labelText: 'تأكيد كلمة المرور', border: OutlineInputBorder())),
      if (error != null) Padding(padding: const EdgeInsets.all(8), child: Text(error!, style: const TextStyle(color: Colors.red), textAlign: TextAlign.center)),
      const SizedBox(height: 16), FilledButton(onPressed: busy ? null : save, child: Text(busy ? 'يرجى الانتظار...' : 'حفظ كلمة المرور')),
    ]),
  ))));
}
'''
source = source[:start] + screens + source[end:]
source = source.replace('DropdownButtonFormField<String>(value:category,', 'DropdownButtonFormField<String>(initialValue:category,')
if 'const PhoneLoginScreen()' in source or 'signInWithOtp(' in source:
    raise SystemExit('Old phone/email OTP login reference remains')
if 'signInWithPassword(' not in source or 'auth.signUp(' not in source or 'AuthChangeEvent.passwordRecovery' not in source:
    raise SystemExit('Password auth verification failed')
source_path.write_text(source, encoding='utf-8')

xml = manifest_path.read_text(encoding='utf-8')
intent = '''
            <intent-filter>
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.BROWSABLE" />
                <data android:scheme="com.ridealgeria.mashwari" android:host="login-callback" />
            </intent-filter>
'''
if 'com.ridealgeria.mashwari' not in xml:
    if '</activity>' not in xml:
        raise SystemExit('Generated Android manifest has no activity element')
    xml = xml.replace('</activity>', intent + '        </activity>', 1)
manifest_path.write_text(xml, encoding='utf-8')
print('Email/password authentication, password recovery, and persisted Supabase session configured.')
