class ApiConfig {
  static const String baseUrl = String.fromEnvironment('API_BASE_URL',
      defaultValue: 'http://10.0.2.2:8000');

  static String? origin(String value) {
    final uri = Uri.tryParse(value.trim());
    if (uri == null ||
        uri.host.isEmpty ||
        uri.userInfo.isNotEmpty ||
        uri.hasQuery ||
        uri.hasFragment ||
        (uri.path.isNotEmpty && uri.path != '/')) {
      return null;
    }
    final loopback = ['127.0.0.1', 'localhost', '10.0.2.2'].contains(uri.host);
    if (uri.scheme != 'https' && !(uri.scheme == 'http' && loopback))
      return null;
    return uri.origin;
  }
}
