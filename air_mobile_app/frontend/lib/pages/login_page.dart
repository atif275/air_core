import 'package:flutter/material.dart';
import 'package:air/pages/home_page.dart';
import 'package:air/pages/signup_page.dart';
import 'package:air/services/logs_manager.dart';
import 'package:local_auth/local_auth.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:io';

class LoginPage extends StatefulWidget {
  final VoidCallback toggleThemeMode;
  final bool isDarkMode;

  const LoginPage({Key? key, required this.toggleThemeMode, required this.isDarkMode}) : super(key: key);

  @override
  _LoginPageState createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> with TickerProviderStateMixin {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading = false;
  bool _obscurePassword = true;
  String? _errorMessage;
  bool _isFaceIdEnabled = false;
  bool _isAuthenticating = false;
  
  late AnimationController _robotAnimationController;
  late AnimationController _pulseAnimationController;
  late Animation<double> _robotFloatAnimation;
  late Animation<double> _pulseAnimation;

  // Hardcoded credentials
  static const String _validUsername = 'admin';
  static const String _validEmail = 'admin@gmail.com';
  static const String _validPassword = 'admin123';

  @override
  void initState() {
    super.initState();
    _initializeAnimations();
    _checkFaceIdAvailability();
  }

  void _initializeAnimations() {
    _robotAnimationController = AnimationController(
      duration: const Duration(seconds: 3),
      vsync: this,
    );
    
    _pulseAnimationController = AnimationController(
      duration: const Duration(seconds: 2),
      vsync: this,
    );

    _robotFloatAnimation = Tween<double>(
      begin: 0.0,
      end: 20.0,
    ).animate(CurvedAnimation(
      parent: _robotAnimationController,
      curve: Curves.easeInOut,
    ));

    _pulseAnimation = Tween<double>(
      begin: 1.0,
      end: 1.2,
    ).animate(CurvedAnimation(
      parent: _pulseAnimationController,
      curve: Curves.easeInOut,
    ));

    _robotAnimationController.repeat(reverse: true);
    _pulseAnimationController.repeat(reverse: true);
  }

  Future<void> _checkFaceIdAvailability() async {
    if (Platform.isIOS) {
      try {
        final localAuth = LocalAuthentication();
        final canCheckBiometrics = await localAuth.canCheckBiometrics;
        final availableBiometrics = await localAuth.getAvailableBiometrics();
        
        // Check if Face ID is available and enabled in settings
        final prefs = await SharedPreferences.getInstance();
        final faceIdEnabled = prefs.getBool('face_id_enabled') ?? false;
        
        setState(() {
          _isFaceIdEnabled = canCheckBiometrics && 
                            availableBiometrics.contains(BiometricType.face) &&
                            faceIdEnabled;
        });
      } catch (e) {
        print('Error checking Face ID availability: $e');
        setState(() {
          _isFaceIdEnabled = false;
        });
      }
    }
  }

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    _robotAnimationController.dispose();
    _pulseAnimationController.dispose();
    super.dispose();
  }

  Future<void> _authenticateWithFaceId() async {
    if (!_isFaceIdEnabled) return;

    setState(() {
      _isAuthenticating = true;
      _errorMessage = null;
    });

    try {
      final localAuth = LocalAuthentication();
      final isAuthenticated = await localAuth.authenticate(
        localizedReason: 'Authenticate to access AIR',
        options: const AuthenticationOptions(
          biometricOnly: true,
          stickyAuth: true,
        ),
      );

      if (isAuthenticated) {
        LogsManager.addLog(
          message: "User authenticated with Face ID",
          source: "Authentication"
        );
        _navigateToHome();
      } else {
        setState(() {
          _errorMessage = 'Face ID authentication failed';
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = 'Face ID not available: $e';
      });
    } finally {
      setState(() {
        _isAuthenticating = false;
      });
    }
  }

  Future<void> _login() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    // Simulate network delay
    await Future.delayed(const Duration(seconds: 1));

    final username = _usernameController.text.trim();
    final password = _passwordController.text;

    // Check credentials
    if ((username == _validUsername || username == _validEmail) && 
        password == _validPassword) {
      
      LogsManager.addLog(
        message: "User logged in successfully: $username",
        source: "Authentication"
      );

      _navigateToHome();
    } else {
      setState(() {
        _errorMessage = 'Invalid username/email or password';
      });
      
      LogsManager.addLog(
        message: "Failed login attempt for: $username",
        source: "Authentication"
      );
    }

    setState(() {
      _isLoading = false;
    });
  }

  void _navigateToHome() {
    if (mounted) {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (context) => HomePage(
            toggleThemeMode: widget.toggleThemeMode,
            isDarkMode: widget.isDarkMode,
          ),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              const Color(0xFF0A0A0A),
              const Color(0xFF1A1A2E),
              const Color(0xFF16213E),
              const Color(0xFF0F3460),
            ],
          ),
        ),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24.0),
              child: Column(
                children: [
                  // Animated Robot Logo
                  AnimatedBuilder(
                    animation: _robotFloatAnimation,
                    builder: (context, child) {
                      return Transform.translate(
                        offset: Offset(0, _robotFloatAnimation.value),
                        child: Container(
                          width: 120,
                          height: 120,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            gradient: LinearGradient(
                              colors: [
                                Colors.blue[400]!,
                                Colors.blue[600]!,
                                Colors.blue[800]!,
                              ],
                            ),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.blue[400]!.withOpacity(0.3),
                                blurRadius: 20,
                                spreadRadius: 5,
                              ),
                            ],
                          ),
                          child: const Icon(
                            Icons.smart_toy,
                            size: 60,
                            color: Colors.white,
                          ),
                        ),
                      );
                    },
                  ),
                  
                  const SizedBox(height: 24),
                  
                  // AIR Title with Glow Effect
                  ShaderMask(
                    shaderCallback: (bounds) => LinearGradient(
                      colors: [
                        Colors.blue[400]!,
                        Colors.cyan[400]!,
                        Colors.blue[600]!,
                      ],
                    ).createShader(bounds),
                    child: const Text(
                      'AIR',
                      style: TextStyle(
                        fontSize: 48,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                        letterSpacing: 8,
                      ),
                    ),
                  ),
                  
                  const SizedBox(height: 8),
                  
                  Text(
                    'Artificial Intelligence Robot',
                    style: TextStyle(
                      fontSize: 16,
                      color: Colors.blue[200],
                      letterSpacing: 2,
                    ),
                  ),
                  
                  const SizedBox(height: 8),
                  
                  Text(
                    'SYSTEM ACCESS',
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.grey[400],
                      letterSpacing: 3,
                      fontWeight: FontWeight.w300,
                    ),
                  ),
                  
                  const SizedBox(height: 40),

                  // Face ID Button (if available)
                  if (_isFaceIdEnabled) ...[
                    AnimatedBuilder(
                      animation: _pulseAnimation,
                      builder: (context, child) {
                        return Transform.scale(
                          scale: _isAuthenticating ? _pulseAnimation.value : 1.0,
                          child: Container(
                            width: double.infinity,
                            height: 60,
                            margin: const EdgeInsets.only(bottom: 24),
                            child: ElevatedButton.icon(
                              onPressed: _isAuthenticating ? null : _authenticateWithFaceId,
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Colors.transparent,
                                foregroundColor: Colors.white,
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(15),
                                  side: BorderSide(
                                    color: Colors.blue[400]!,
                                    width: 2,
                                  ),
                                ),
                                elevation: 0,
                              ),
                              icon: _isAuthenticating
                                  ? const SizedBox(
                                      width: 20,
                                      height: 20,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                        valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                                      ),
                                    )
                                  : const Icon(Icons.face, size: 24),
                              label: Text(
                                _isAuthenticating ? 'Authenticating...' : 'Login with Face ID',
                                style: const TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                          ),
                        );
                      },
                    ),
                    
                    // Divider with "OR"
                    Row(
                      children: [
                        Expanded(
                          child: Container(
                            height: 1,
                            color: Colors.grey[600],
                          ),
                        ),
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 16),
                          child: Text(
                            'OR',
                            style: TextStyle(
                              color: Colors.grey[400],
                              fontSize: 12,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ),
                        Expanded(
                          child: Container(
                            height: 1,
                            color: Colors.grey[600],
                          ),
                        ),
                      ],
                    ),
                    
                    const SizedBox(height: 24),
                  ],

                  // Login Form Card
                  Container(
                    decoration: BoxDecoration(
                      color: Colors.black.withOpacity(0.3),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                        color: Colors.blue[400]!.withOpacity(0.3),
                        width: 1,
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.blue[400]!.withOpacity(0.1),
                          blurRadius: 20,
                          spreadRadius: 5,
                        ),
                      ],
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(24.0),
                      child: Form(
                        key: _formKey,
                        child: Column(
                          children: [
                            // Username/Email Field
                            TextFormField(
                              controller: _usernameController,
                              style: const TextStyle(color: Colors.white),
                              decoration: InputDecoration(
                                labelText: 'Username or Email',
                                labelStyle: TextStyle(color: Colors.blue[200]),
                                hintText: 'Enter your username or email',
                                hintStyle: TextStyle(color: Colors.grey[500]),
                                prefixIcon: Icon(Icons.person, color: Colors.blue[300]),
                                border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(12),
                                  borderSide: BorderSide(color: Colors.blue[400]!),
                                ),
                                enabledBorder: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(12),
                                  borderSide: BorderSide(color: Colors.blue[400]!.withOpacity(0.5)),
                                ),
                                focusedBorder: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(12),
                                  borderSide: BorderSide(color: Colors.blue[400]!, width: 2),
                                ),
                                filled: true,
                                fillColor: Colors.black.withOpacity(0.2),
                              ),
                              validator: (value) {
                                if (value == null || value.trim().isEmpty) {
                                  return 'Please enter your username or email';
                                }
                                return null;
                              },
                            ),
                            const SizedBox(height: 16),

                            // Password Field
                            TextFormField(
                              controller: _passwordController,
                              obscureText: _obscurePassword,
                              style: const TextStyle(color: Colors.white),
                              decoration: InputDecoration(
                                labelText: 'Password',
                                labelStyle: TextStyle(color: Colors.blue[200]),
                                hintText: 'Enter your password',
                                hintStyle: TextStyle(color: Colors.grey[500]),
                                prefixIcon: Icon(Icons.lock, color: Colors.blue[300]),
                                suffixIcon: IconButton(
                                  icon: Icon(
                                    _obscurePassword ? Icons.visibility : Icons.visibility_off,
                                    color: Colors.blue[300],
                                  ),
                                  onPressed: () {
                                    setState(() {
                                      _obscurePassword = !_obscurePassword;
                                    });
                                  },
                                ),
                                border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(12),
                                  borderSide: BorderSide(color: Colors.blue[400]!),
                                ),
                                enabledBorder: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(12),
                                  borderSide: BorderSide(color: Colors.blue[400]!.withOpacity(0.5)),
                                ),
                                focusedBorder: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(12),
                                  borderSide: BorderSide(color: Colors.blue[400]!, width: 2),
                                ),
                                filled: true,
                                fillColor: Colors.black.withOpacity(0.2),
                              ),
                              validator: (value) {
                                if (value == null || value.isEmpty) {
                                  return 'Please enter your password';
                                }
                                return null;
                              },
                            ),
                            const SizedBox(height: 24),

                            // Error Message
                            if (_errorMessage != null)
                              Container(
                                width: double.infinity,
                                padding: const EdgeInsets.all(12),
                                decoration: BoxDecoration(
                                  color: Colors.red[900]!.withOpacity(0.3),
                                  borderRadius: BorderRadius.circular(8),
                                  border: Border.all(color: Colors.red[400]!),
                                ),
                                child: Text(
                                  _errorMessage!,
                                  style: TextStyle(
                                    color: Colors.red[200],
                                    fontSize: 14,
                                  ),
                                ),
                              ),

                            if (_errorMessage != null) const SizedBox(height: 16),

                            // Login Button
                            Container(
                              width: double.infinity,
                              height: 50,
                              child: ElevatedButton(
                                onPressed: _isLoading ? null : _login,
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: Colors.blue[600],
                                  foregroundColor: Colors.white,
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  elevation: 8,
                                  shadowColor: Colors.blue[400]!.withOpacity(0.5),
                                ),
                                child: _isLoading
                                    ? const SizedBox(
                                        height: 20,
                                        width: 20,
                                        child: CircularProgressIndicator(
                                          strokeWidth: 2,
                                          valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                                        ),
                                      )
                                    : const Text(
                                        'ACCESS SYSTEM',
                                        style: TextStyle(
                                          fontSize: 16,
                                          fontWeight: FontWeight.bold,
                                          letterSpacing: 1,
                                        ),
                                      ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),

                  const SizedBox(height: 24),

                  // Demo Credentials Info
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.blue[900]!.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: Colors.blue[400]!.withOpacity(0.3)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(Icons.info_outline, color: Colors.blue[300], size: 20),
                            const SizedBox(width: 8),
                            Text(
                              'Demo Credentials',
                              style: TextStyle(
                                color: Colors.blue[200],
                                fontWeight: FontWeight.bold,
                                fontSize: 14,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Username/Email: admin or admin@gmail.com',
                          style: TextStyle(
                            color: Colors.blue[100],
                            fontSize: 12,
                          ),
                        ),
                        Text(
                          'Password: admin123',
                          style: TextStyle(
                            color: Colors.blue[100],
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 24),

                  // Sign Up Link
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        "New to AIR? ",
                        style: TextStyle(
                          color: Colors.grey[400],
                          fontSize: 14,
                        ),
                      ),
                      TextButton(
                        onPressed: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) => SignupPage(
                                toggleThemeMode: widget.toggleThemeMode,
                                isDarkMode: widget.isDarkMode,
                              ),
                            ),
                          );
                        },
                        child: Text(
                          'Create Account',
                          style: TextStyle(
                            color: Colors.blue[400],
                            fontWeight: FontWeight.bold,
                            fontSize: 14,
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
} 