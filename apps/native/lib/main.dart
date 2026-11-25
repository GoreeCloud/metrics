import 'dart:async';
import 'api_client.dart';
import 'session_epoch.dart';
import 'package:goreecloud_ui_expressive/goreecloud_ui_expressive.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

void main() => runApp(const MetricsApp());

// Network rates are never inferred from single samples or reset counters.
String formatNetworkRate(Map<String, dynamic>? reading, String field) {
  final value = reading?[field];
  if (reading?['state'] != 'ok' ||
      value is! num ||
      !value.isFinite ||
      value < 0) {
    return '—';
  }
  var amount = value.toDouble();
  var unit = 0;
  const units = ['B/s', 'KiB/s', 'MiB/s', 'GiB/s', 'TiB/s'];
  while (amount >= 1024 && unit < units.length - 1) {
    amount /= 1024;
    unit++;
  }
  final precision = unit == 0 && amount >= 10 ? 0 : 1;
  return '${amount.toStringAsFixed(precision)} ${units[unit]}';
}

String networkRateStatus(Map<String, dynamic>? reading) {
  switch (reading?['state']) {
    case 'ok':
      return 'Computed from consecutive host samples';
    case 'insufficient_samples':
      return 'Waiting for another host sample';
    case 'counter_reset':
      return 'Host restart or network counter reset';
    case 'invalid_interval':
      return 'Invalid or stale sample interval';
    default:
      return 'Network rate unavailable';
  }
}

class MetricsApp extends StatelessWidget {
  const MetricsApp({super.key});
  @override
  Widget build(BuildContext context) {
    ThemeData theme(Brightness brightness) => GoreeCloudFlutterTheme.build(
          brightness: brightness,
          accent: GoreeAccent.lagoon,
        );

    return MaterialApp(
      title: 'GoreeCloud Metrics',
      debugShowCheckedModeBanner: false,
      theme: theme(Brightness.light),
      darkTheme: theme(Brightness.dark),
      home: const MetricsHome(),
    );
  }
}

class MetricsHome extends StatefulWidget {
  const MetricsHome({super.key});
  @override
  State<MetricsHome> createState() => _MetricsHomeState();
}

class _MetricsHomeState extends State<MetricsHome> {
  final hubField = TextEditingController();
  final tokenField = TextEditingController();
  final client = http.Client();
  final sessionEpoch = MetricsSessionEpoch();
  String? hub, token, message, selected;
  bool busy = false;
  List<Map<String, dynamic>> machines = [], alerts = [], samples = [];
  List<Map<String, dynamic>> containers = [], alertEvents = [];
  Map<String, dynamic>? networkRate;
  int historyHours = 24;
  Timer? timer;

  @override
  void dispose() {
    sessionEpoch.invalidate();
    timer?.cancel();
    hubField.dispose();
    tokenField.dispose();
    client.close();
    super.dispose();
  }

  Future<dynamic> getData(String path) async {
    return fetchMetricsJson(client, Uri.parse(hub! + path), token!);
  }

  List<Map<String, dynamic>> objects(dynamic value) =>
      (value as List).map((e) => Map<String, dynamic>.from(e as Map)).toList();

  bool isCurrentSession(int ticket) =>
      mounted && hub != null && sessionEpoch.accepts(ticket);

  Future<void> connect() async {
    final raw = hubField.text.trim().replaceAll(RegExp(r'/+$'), '');
    Uri? uri;
    try {
      uri = Uri.parse(raw);
    } catch (_) {}
    final local =
        uri != null && ['localhost', '127.0.0.1', '::1'].contains(uri.host);
    if (uri == null ||
        !uri.hasAuthority ||
        (uri.scheme != 'https' && !(uri.scheme == 'http' && local)) ||
        uri.userInfo.isNotEmpty ||
        uri.hasQuery ||
        uri.hasFragment ||
        uri.path.isNotEmpty ||
        tokenField.text.trim().length < 32) {
      setState(() =>
          message = 'Use an HTTPS hub URL and a valid administrator token.');
      return;
    }
    final ticket = sessionEpoch.invalidate();
    setState(() {
      hub = raw;
      token = tokenField.text.trim();
      message = null;
      busy = false;
    });
    await refresh();
    if (isCurrentSession(ticket) && message == null) {
      timer?.cancel();
      timer = Timer.periodic(const Duration(seconds: 20), (_) => refresh());
    }
  }

  Future<void> refresh() async {
    if (hub == null || busy) return;
    final ticket = sessionEpoch.snapshot;
    setState(() => busy = true);
    try {
      final results = await Future.wait([
        getData('/api/v1/systems'),
        getData('/api/v1/alerts'),
      ]);
      final next = objects(results[0]['systems']);
      if (!isCurrentSession(ticket)) return;
      setState(() {
        machines = next;
        alerts = objects(results[1]['alerts']);
        final previous = selected;
        selected = next.any((m) => m['node_id'] == selected)
            ? selected
            : (next.isEmpty ? null : next.first['node_id'] as String);
        if (selected != previous) {
          samples = [];
          containers = [];
          networkRate = null;
        }
        message = null;
      });
      await Future.wait([
        loadHistory(),
        loadContainers(),
        loadNetworkRate(),
        loadAlertEvents()
      ]);
    } catch (_) {
      if (isCurrentSession(ticket)) {
        setState(() => message =
            'Cannot reach the hub. Check your URL, connection and token.');
      }
    } finally {
      if (isCurrentSession(ticket)) setState(() => busy = false);
    }
  }

  Future<void> loadHistory() async {
    final ticket = sessionEpoch.snapshot;
    final id = selected;
    final hours = historyHours;
    if (id == null) {
      if (mounted) setState(() => samples = []);
      return;
    }
    try {
      final response = await getData(
          '/api/v1/systems/${Uri.encodeComponent(id)}/history?hours=$hours&points=400');
      if (isCurrentSession(ticket) && selected == id && historyHours == hours) {
        setState(() => samples = objects(response['samples']));
      }
    } catch (_) {
      if (isCurrentSession(ticket) && selected == id && historyHours == hours) {
        setState(() => samples = []);
      }
    }
  }

  Future<void> loadContainers() async {
    final ticket = sessionEpoch.snapshot;
    final id = selected;
    if (id == null) {
      if (mounted) setState(() => containers = []);
      return;
    }
    try {
      final response = await getData(
          '/api/v1/systems/${Uri.encodeComponent(id)}/containers');
      if (isCurrentSession(ticket) && selected == id) {
        setState(() => containers = objects(response['containers']));
      }
    } catch (_) {
      if (isCurrentSession(ticket) && selected == id) {
        setState(() => containers = []);
      }
    }
  }

  Future<void> loadNetworkRate() async {
    final ticket = sessionEpoch.snapshot;
    final id = selected;
    if (id == null) {
      if (mounted) setState(() => networkRate = null);
      return;
    }
    try {
      final response = await getData(
          '/api/v1/systems/${Uri.encodeComponent(id)}/network-rate');
      final result = Map<String, dynamic>.from(response as Map);
      if (isCurrentSession(ticket) && selected == id) {
        setState(() => networkRate = result);
      }
    } catch (_) {
      if (isCurrentSession(ticket) && selected == id) {
        setState(() => networkRate = null);
      }
    }
  }

  Future<void> loadAlertEvents() async {
    final ticket = sessionEpoch.snapshot;
    try {
      final response = await getData('/api/v1/alert-events?limit=30');
      if (isCurrentSession(ticket)) {
        setState(() => alertEvents = objects(response['events']));
      }
    } catch (_) {
      if (isCurrentSession(ticket)) setState(() => alertEvents = []);
    }
  }

  void disconnect() {
    sessionEpoch.invalidate();
    timer?.cancel();
    setState(() {
      hub = null;
      token = null;
      busy = false;
      selected = null;
      machines = [];
      alerts = [];
      samples = [];
      containers = [];
      networkRate = null;
      historyHours = 24;
      alertEvents = [];
      message = null;
      tokenField.clear();
    });
  }

  double number(Map<String, dynamic> m, String key) =>
      (m[key] as num?)?.toDouble() ?? 0;

  Widget gauge(String label, double value, IconData icon) {
    final clipped = value.clamp(0.0, 100.0);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 9),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(icon, size: 18),
          const SizedBox(width: 8),
          Expanded(child: Text(label)),
          Text('${value.toStringAsFixed(1)}%',
              style: const TextStyle(fontWeight: FontWeight.bold)),
        ]),
        const SizedBox(height: 8),
        LinearProgressIndicator(
            value: clipped / 100,
            minHeight: 7,
            borderRadius: BorderRadius.circular(8)),
      ]),
    );
  }

  Widget login() => Center(
          child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 490),
        child: Card(
            child: Padding(
                padding: const EdgeInsets.all(28),
                child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.monitor_heart_outlined, size: 40),
                      const SizedBox(height: 20),
                      Text('Your systems, in view.',
                          style: Theme.of(context).textTheme.headlineMedium),
                      const SizedBox(height: 10),
                      const Text(
                          'Connect to your trusted Metrics hub. Credentials remain in app memory only.'),
                      const SizedBox(height: 24),
                      TextField(
                          controller: hubField,
                          keyboardType: TextInputType.url,
                          decoration: const InputDecoration(
                              labelText: 'Hub URL (HTTPS)',
                              hintText: 'https://metrics.example.com',
                              border: OutlineInputBorder())),
                      const SizedBox(height: 14),
                      TextField(
                          controller: tokenField,
                          obscureText: true,
                          enableSuggestions: false,
                          autocorrect: false,
                          decoration: const InputDecoration(
                              labelText: 'Administrator token',
                              border: OutlineInputBorder())),
                      const SizedBox(height: 18),
                      FilledButton.icon(
                          onPressed: busy ? null : connect,
                          icon: const Icon(Icons.login),
                          label: const Text('Connect to hub')),
                      if (message != null)
                        Padding(
                            padding: const EdgeInsets.only(top: 12),
                            child: Text(message!,
                                style: TextStyle(
                                    color:
                                        Theme.of(context).colorScheme.error))),
                      const SizedBox(height: 12),
                      const Text('GoreeCloud UI · Lagoon theme',
                          style: TextStyle(fontSize: 12)),
                    ]))),
      ));

  Widget overviewCard(String title, String value, IconData icon) => SizedBox(
      width: 160,
      child: Card(
          child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(icon),
          const SizedBox(height: 10),
          Text(value, style: Theme.of(context).textTheme.headlineMedium),
          Text(title),
        ]),
      )));

  Widget dashboard() {
    final matches = machines.where((m) => m['node_id'] == selected).toList();
    final current = matches.isEmpty ? null : matches.first;
    final currentRate =
        networkRate?['node_id'] == selected ? networkRate : null;
    final online = machines.where((m) => m['online'] == true).length;
    return RefreshIndicator(
      onRefresh: refresh,
      child: ListView(padding: const EdgeInsets.all(20), children: [
        Wrap(spacing: 12, runSpacing: 12, children: [
          overviewCard(
              'Systems', machines.length.toString(), Icons.dns_outlined),
          overviewCard('Online', online.toString(), Icons.check_circle_outline),
          overviewCard(
              'Alerts', alerts.length.toString(), Icons.notifications_none),
        ]),
        const SizedBox(height: 26),
        Text('Systems', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 8),
        if (machines.isEmpty)
          const Card(
              child: ListTile(
                  title: Text('No connected agents'),
                  subtitle:
                      Text('Configure an agent to send its first sample.'))),
        ...machines.map((m) => Card(
                child: ListTile(
              selected: m['node_id'] == selected,
              leading: Icon(Icons.computer,
                  color: m['online'] == true ? Colors.teal : Colors.grey),
              title: Text((m['hostname'] ?? '').toString()),
              subtitle: Text((m['node_id'] ?? '').toString() +
                  (m['online'] == true ? ' · Online' : ' · Offline')),
              trailing: Text('${number(m, 'cpu').toStringAsFixed(0)}% CPU'),
              onTap: () {
                setState(() {
                  selected = m['node_id'] as String;
                  samples = [];
                  containers = [];
                  networkRate = null;
                });
                loadHistory();
                loadContainers();
                loadNetworkRate();
              },
            ))),
        if (current != null) ...[
          const SizedBox(height: 22),
          Text(
              'Host details · last ${historyHours == 168 ? '7 days' : '$historyHours hours'}',
              style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 10),
          SegmentedButton<int>(
            showSelectedIcon: false,
            segments: const [
              ButtonSegment(value: 6, label: Text('6h')),
              ButtonSegment(value: 24, label: Text('24h')),
              ButtonSegment(value: 168, label: Text('7d')),
            ],
            selected: {historyHours},
            onSelectionChanged: (values) {
              setState(() {
                historyHours = values.first;
                samples = [];
              });
              loadHistory();
            },
          ),
          const SizedBox(height: 10),
          Card(
              child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(children: [
                    gauge('CPU', number(current, 'cpu'), Icons.memory_outlined),
                    gauge('Memory', number(current, 'memory'),
                        Icons.storage_outlined),
                    gauge('Disk', number(current, 'disk'), Icons.save_outlined),
                    const SizedBox(height: 16),
                    SizedBox(
                        height: 150,
                        width: double.infinity,
                        child: CustomPaint(
                            painter: MetricsChart(samples,
                                color: Theme.of(context).colorScheme.primary))),
                    const SizedBox(height: 8),
                    const Text('CPU utilization history · 0–100%',
                        style: TextStyle(fontSize: 12)),
                  ]))),
          const SizedBox(height: 22),
          Text('Network transfer rates',
              style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Card(
              child: Column(children: [
            ListTile(
                leading: const Icon(Icons.download_outlined),
                title: const Text('Received per second'),
                subtitle: Text(networkRateStatus(currentRate)),
                trailing: Text(
                    formatNetworkRate(currentRate, 'rx_bytes_per_second'))),
            const Divider(height: 1),
            ListTile(
                leading: const Icon(Icons.upload_outlined),
                title: const Text('Sent per second'),
                subtitle: Text(networkRateStatus(currentRate)),
                trailing: Text(
                    formatNetworkRate(currentRate, 'tx_bytes_per_second'))),
          ])),
          const SizedBox(height: 22),
          Text('Container snapshots',
              style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          if (containers.isEmpty)
            const Card(
                child: ListTile(
              leading: Icon(Icons.view_in_ar_outlined),
              title: Text('Container telemetry is optional'),
              subtitle: Text(
                  'Enable a supported Podman/Docker collector on the host to view snapshots.'),
            )),
          ...containers.map((c) => Card(
                  child: ListTile(
                leading: const Icon(Icons.widgets_outlined),
                title: Text((c['name'] ?? '').toString()),
                subtitle:
                    Text('Memory: ${number(c, 'memory').toStringAsFixed(1)}%'),
                trailing: Text('CPU ${number(c, 'cpu').toStringAsFixed(1)}%'),
              ))),
        ],
        const SizedBox(height: 22),
        Text('Current indicators',
            style: Theme.of(context).textTheme.titleLarge),
        if (alerts.isEmpty)
          const Card(
              child: ListTile(
            leading: Icon(Icons.verified_user_outlined),
            title: Text('No current alerts'),
            subtitle:
                Text('Hub-configurable thresholds · Default 90% / 120 seconds'),
          )),
        ...alerts.map((a) => Card(
                child: ListTile(
              leading: const Icon(Icons.warning_amber_rounded),
              title: Text('${a['node_id'] ?? ''} · ${a['metric'] ?? ''}'),
              subtitle: Text((a['message'] ?? '').toString()),
            ))),
        const SizedBox(height: 22),
        Text('Recent alert transitions',
            style: Theme.of(context).textTheme.titleLarge),
        if (alertEvents.isEmpty)
          const Card(
              child: ListTile(
            title: Text('No recorded transitions'),
            subtitle:
                Text('The optional alert worker must run to journal events.'),
          )),
        ...alertEvents.map((event) => Card(
                child: ListTile(
              leading: Icon(event['state'] == 'resolved'
                  ? Icons.check_circle_outline
                  : Icons.warning_amber_outlined),
              title:
                  Text('${event['node_id'] ?? ''} · ${event['metric'] ?? ''}'),
              subtitle: Text((event['message'] ?? '').toString()),
              trailing: Text((event['state'] ?? '').toString()),
            ))),
        const SizedBox(height: 22),
        const Text(
            'Development preview · External notification delivery is opt-in',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 12)),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
            title: const Text('GoreeCloud Metrics'),
            actions: hub == null
                ? []
                : [
                    IconButton(
                        onPressed: busy ? null : refresh,
                        tooltip: 'Refresh',
                        icon: const Icon(Icons.refresh)),
                    IconButton(
                        onPressed: disconnect,
                        tooltip: 'Disconnect',
                        icon: const Icon(Icons.logout)),
                  ]),
        body: hub == null
            ? Padding(padding: const EdgeInsets.all(16), child: login())
            : Column(children: [
                if (message != null)
                  MaterialBanner(content: Text(message!), actions: [
                    TextButton(onPressed: refresh, child: const Text('Retry')),
                  ]),
                Expanded(child: dashboard()),
              ]),
      );
}

class MetricsChart extends CustomPainter {
  const MetricsChart(this.samples, {required this.color});
  final List<Map<String, dynamic>> samples;
  final Color color;
  @override
  void paint(Canvas canvas, Size size) {
    final guide = Paint()
      ..color = color.withValues(alpha: .16)
      ..strokeWidth = 1;
    for (var i = 0; i <= 4; i++) {
      final y = size.height * i / 4;
      canvas.drawLine(Offset(0, y), Offset(size.width, y), guide);
    }
    if (samples.length < 2) return;
    final points =
        samples.map((s) => (s['cpu'] as num?)?.toDouble() ?? 0).toList();
    final path = Path();
    for (var i = 0; i < points.length; i++) {
      final point = Offset(
        size.width * i / (points.length - 1),
        size.height * (1 - points[i].clamp(0.0, 100.0) / 100),
      );
      if (i == 0) {
        path.moveTo(point.dx, point.dy);
      } else {
        path.lineTo(point.dx, point.dy);
      }
    }
    canvas.drawPath(
        path,
        Paint()
          ..color = color
          ..strokeWidth = 2.5
          ..style = PaintingStyle.stroke
          ..strokeJoin = StrokeJoin.round);
  }

  @override
  bool shouldRepaint(covariant MetricsChart oldDelegate) =>
      oldDelegate.samples != samples || oldDelegate.color != color;
}
