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


# Improve GPS precision and provide explicit free OpenStreetMap place search.
app_root = source_path.parent.parent
pubspec_path = app_root / "pubspec.yaml"
map_source = source_path.read_text(encoding="utf-8")
if "import 'dart:convert';" not in map_source:
    map_source = map_source.replace("import 'dart:async';", "import 'dart:async';\nimport 'dart:convert';\nimport 'package:http/http.dart' as http;")

old_search = """  Future<void> searchPlaces(String query) async {
    searchTimer?.cancel();
    if (query.trim().length < 2) { setState(() => suggestions = []); return; }
    searchTimer = Timer(const Duration(milliseconds: 350), () async {
      try {
        final result = await Supabase.instance.client.functions.invoke('search-places', body: {'query': query.trim()});
        final rows = (result.data as Map)['places'] as List? ?? [];
        if (mounted) setState(() => suggestions = rows.cast<Map<String,dynamic>>());
      } catch (_) { if (mounted) setState(() => suggestions = []); }
    });
  }
"""
new_search = r'''  final Map<String, List<Map<String,dynamic>>> _placeSearchCache = {};
  DateTime? _lastPlaceSearchAt;
  Future<void> searchPlaces(String query) async {
    searchTimer?.cancel();
    final term = query.trim();
    if (term.length < 2) { if (mounted) setState(() => suggestions = []); return; }
    searchTimer = Timer(const Duration(milliseconds: 250), () async {
      if (!mounted) return;
      setState(() { error = null; suggestions = []; });
      final cacheKey = term.toLowerCase();
      final cached = _placeSearchCache[cacheKey];
      if (cached != null) { if (mounted) setState(() => suggestions = cached); return; }
      try {
        // Nominatim public service: explicit searches only, not keystroke autocomplete.
        final last = _lastPlaceSearchAt;
        if (last != null) {
          final wait = const Duration(milliseconds: 1100) - DateTime.now().difference(last);
          if (wait > Duration.zero) await Future<void>.delayed(wait);
        }
        _lastPlaceSearchAt = DateTime.now();
        final uri = Uri.https('nominatim.openstreetmap.org', '/search', {
          'format': 'jsonv2', 'q': term + ', Algeria', 'countrycodes': 'dz',
          'limit': '8', 'addressdetails': '1', 'accept-language': 'ar,fr,en',
        });
        final response = await http.get(uri, headers: {
          'User-Agent': 'MashwariPassenger/1.0 (Android; OpenStreetMap search)',
          'Accept': 'application/json',
        }).timeout(const Duration(seconds: 15));
        if (response.statusCode != 200) throw Exception('خدمة البحث عن الأماكن غير متاحة حالياً.');
        final raw = jsonDecode(response.body);
        if (raw is! List) throw Exception('نتيجة البحث غير صالحة.');
        final rows = raw.whereType<Map>().where((p) => p['lat'] != null && p['lon'] != null)
          .map((p) => <String,dynamic>{
            'label': (p['name']?.toString().trim().isNotEmpty == true ? p['name'].toString() + ', ' : '') + (p['display_name']?.toString() ?? 'مكان'),
            'latitude': double.tryParse(p['lat'].toString()),
            'longitude': double.tryParse(p['lon'].toString()),
            'type': p['type']?.toString() ?? '',
          }).where((p) => p['latitude'] != null && p['longitude'] != null).toList();
        _placeSearchCache[cacheKey] = rows;
        if (mounted) setState(() => suggestions = rows);
        if (rows.isEmpty && mounted) setState(() => error = 'ما لقيناش نتائج. جرّب اسم المكان أو الحي بالفرنسية أو العربية.');
      } catch (e) {
        if (mounted) setState(() => error = e.toString().replaceFirst('Exception: ', 'تعذر البحث عن المكان: '));
      }
    });
  }
'''
if old_search in map_source:
    map_source = map_source.replace(old_search, new_search)
elif "nominatim.openstreetmap.org" not in map_source:
    raise SystemExit("Original place search function not found")

old_locate = """  Future<void> locate() async {
    setState(() { locating = true; error = null; });
    try {
      if (!await Geolocator.isLocationServiceEnabled()) throw Exception('فعّل خدمة تحديد الموقع في الهاتف.');
      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied || permission == LocationPermission.deniedForever) throw Exception('يلزم السماح بالوصول إلى الموقع.');
      final pos = await Geolocator.getCurrentPosition(locationSettings: const LocationSettings(accuracy: LocationAccuracy.high));
      final point = LatLng(pos.latitude, pos.longitude);
      setState(() { pickup = point; selectingPickup = false; pickupLabel = 'موقعي الحالي'; });
      mapController.move(point, 15);
    } catch (e) { setState(() => error = e.toString().replaceFirst('Exception: ', '')); }
    finally { if (mounted) setState(() => locating = false); }
  }
"""
new_locate = r'''  Future<void> locate() async {
    if (mounted) setState(() { locating = true; error = null; });
    try {
      if (!await Geolocator.isLocationServiceEnabled()) throw Exception('فعّل خدمة تحديد الموقع GPS في الهاتف.');
      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied || permission == LocationPermission.deniedForever) throw Exception('اسمح لمشواري بالوصول إلى الموقع أثناء الاستخدام.');
      final permissionAccuracy = await Geolocator.getLocationAccuracy();
      if (permissionAccuracy == LocationAccuracyStatus.reduced) {
        throw Exception('صلاحية الموقع التقريبي مفعّلة. افتح إعدادات التطبيق > الأذونات > الموقع، واختر السماح بالموقع الدقيق.');
      }
      Position? best;
      for (var attempt = 0; attempt < 2; attempt++) {
        final pos = await Geolocator.getCurrentPosition(locationSettings: LocationSettings(
          accuracy: LocationAccuracy.bestForNavigation,
          distanceFilter: 0,
          timeLimit: const Duration(seconds: 20),
        ));
        if (best == null || pos.accuracy < best.accuracy) best = pos;
        if (best.accuracy <= 20) break;
        if (attempt == 0) await Future<void>.delayed(const Duration(seconds: 2));
      }
      if (best == null) throw Exception('تعذر الحصول على موقع GPS. حاول في مكان مفتوح.');
      final point = LatLng(best.latitude, best.longitude);
      final accuracy = best.accuracy.round();
      if (!mounted) return;
      setState(() {
        pickup = point;
        selectingPickup = false;
        pickupLabel = 'موقعي الحالي • دقة تقريباً ±' + accuracy.toString() + 'م';
        if (accuracy > 50) error = 'إشارة GPS ضعيفة (±' + accuracy.toString() + 'م). جرّب الخروج لمكان مفتوح أو فعّل الموقع الدقيق.';
      });
      mapController.move(point, 18);
    } catch (e) {
      if (mounted) setState(() => error = e.toString().replaceFirst('Exception: ', ''));
    } finally { if (mounted) setState(() => locating = false); }
  }
'''
if old_locate in map_source:
    map_source = map_source.replace(old_locate, new_locate)
elif "LocationAccuracy.bestForNavigation" not in map_source:
    raise SystemExit("Original GPS function not found")

old_field = """TextField(controller: destinationSearch, onChanged: searchPlaces, decoration: const InputDecoration(
          labelText: 'ابحث عن الوجهة أو اخترها من الخريطة', prefixIcon: Icon(Icons.search), border: OutlineInputBorder(), isDense: true)),"""
new_field = """TextField(controller: destinationSearch, onSubmitted: searchPlaces, decoration: InputDecoration(
          labelText: 'ابحث عن عيادة أو عنوان أو مكان', prefixIcon: const Icon(Icons.search), border: const OutlineInputBorder(), isDense: true,
          suffixIcon: IconButton(icon: const Icon(Icons.search), onPressed: () => searchPlaces(destinationSearch.text)))),"""
if old_field in map_source:
    map_source = map_source.replace(old_field, new_field)
elif "onSubmitted: searchPlaces" not in map_source:
    raise SystemExit("Original destination search field not found")

old_markers = """          MarkerLayer(markers: [if (pickup != null) Marker(point: pickup!, width: 42, height: 42, child: const Icon(Icons.my_location, color: Colors.blue, size: 34)),
            if (dropoff != null) Marker(point: dropoff!, width: 42, height: 42, child: const Icon(Icons.location_on, color: Colors.red, size: 38))]),"""
new_markers = """          MarkerLayer(markers: [
            if (pickup != null) Marker(point: pickup!, width: 42, height: 42, child: const Icon(Icons.my_location, color: Colors.blue, size: 34)),
            if (dropoff != null) Marker(point: dropoff!, width: 42, height: 42, child: const Icon(Icons.location_on, color: Colors.red, size: 38)),
            ...suggestions.where((p) => p['latitude'] is num && p['longitude'] is num).map((p) => Marker(
              point: LatLng((p['latitude'] as num).toDouble(), (p['longitude'] as num).toDouble()),
              width: 38, height: 38,
              child: GestureDetector(onTap: () => choosePlace(p), child: const Icon(Icons.place, color: Colors.deepOrange, size: 34)),
            )),
          ]),"""
if old_markers in map_source:
    map_source = map_source.replace(old_markers, new_markers)
elif "suggestions.where((p)" not in map_source:
    raise SystemExit("Original marker layer not found")

source_path.write_text(map_source, encoding="utf-8")
pub = pubspec_path.read_text(encoding="utf-8")
if "\n  http:" not in pub:
    pub = pub.replace("  geolocator: ^14.1.2", "  geolocator: ^14.1.2\n  http: ^1.5.0")
pubspec_path.write_text(pub, encoding="utf-8")
print("Precise GPS and explicit OpenStreetMap place search configured.")


# Add a direct Google Maps directions hand-off for the selected destination.
map_source = source_path.read_text(encoding="utf-8")
if "package:url_launcher/url_launcher.dart" not in map_source:
    map_source = map_source.replace(
        "import 'package:http/http.dart' as http;",
        "import 'package:http/http.dart' as http;\nimport 'package:url_launcher/url_launcher.dart';",
    )
if "Future<void> openInGoogleMaps()" not in map_source:
    anchor = "  Future<void> openQuotes() async {"
    route_method = r'''  Future<void> openInGoogleMaps() async {
    if (dropoff == null) {
      if (mounted) setState(() => error = 'اختار المكان من نتائج البحث أولاً.');
      return;
    }
    try {
      if (pickup == null) await locate();
      final destination = dropoff!.latitude.toString() + ',' + dropoff!.longitude.toString();
      final params = <String, String>{
        'api': '1',
        'destination': destination,
        'travelmode': 'driving',
      };
      if (pickup != null) {
        params['origin'] = pickup!.latitude.toString() + ',' + pickup!.longitude.toString();
      }
      final uri = Uri.https('www.google.com', '/maps/dir/', params);
      final opened = await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (!opened && mounted) setState(() => error = 'تعذر فتح Google Maps. تأكد من تثبيته أو افتح المتصفح.');
    } catch (_) {
      if (mounted) setState(() => error = 'تعذر فتح الطريق. تحقق من الاتصال وحاول مجدداً.');
    }
  }
'''
    if anchor not in map_source:
        raise SystemExit("Could not find BookingScreen openQuotes insertion point")
    map_source = map_source.replace(anchor, route_method + anchor, 1)

if "الطريق إلى المكان في Google Maps" not in map_source:
    anchor = "        if (error != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text(error!, style: const TextStyle(color: Colors.red))),"
    button = """        if (dropoff != null) ...[
          const SizedBox(height: 8),
          FilledButton.tonalIcon(
            onPressed: openInGoogleMaps,
            icon: const Icon(Icons.directions),
            label: const Text('الطريق إلى المكان في Google Maps'),
          ),
        ],
"""
    if anchor not in map_source:
        raise SystemExit("Could not find BookingScreen error display insertion point")
    map_source = map_source.replace(anchor, button + anchor, 1)

source_path.write_text(map_source, encoding="utf-8")
pubspec_path = source_path.parent.parent / "pubspec.yaml"
pub = pubspec_path.read_text(encoding="utf-8")
if "\n  url_launcher:" not in pub:
    pub = pub.replace("  http: ^1.5.0", "  http: ^1.5.0\n  url_launcher: ^6.3.2")
pubspec_path.write_text(pub, encoding="utf-8")
print("Place search selection and Google Maps directions action configured.")
