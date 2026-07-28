/// API Configuration
/// Change these values based on your environment
library;

class ApiConfig {
  // Development - Android Emulator
  static const String baseUrl = 'http://10.97.118.201:8000';
  
  // Development - iOS Simulator
  // static const String baseUrl = 'http://localhost:8000';
  
  // Production
  // static const String baseUrl = 'https://api.recoverycompanion.app';
  
  // Connection timeout in milliseconds
  static const int connectTimeout = 30000;
  
  // Receive timeout in milliseconds
  static const int receiveTimeout = 30000;
}
