# monitoring/detectors/screen_sharing_detector.py
import logging
import platform
import subprocess
import re
from typing import Dict, List, Optional, Tuple
import psutil
import time
from datetime import datetime


logger = logging.getLogger(__name__)


class ScreenSharingDetector:
    def __init__(self, config: Optional[Dict] = None):
        self.system = platform.system().lower()
        self.config = config or self._get_default_config()
        self.screen_sharing_apps = self._get_screen_sharing_apps()
        self.virtual_display_indicators = self._get_virtual_display_indicators()
        
    def _get_default_config(self) -> Dict:
        return {
            'strict_mode': True,  # If True, blocks test on any detection
            'allowed_browsers': ['chrome', 'firefox', 'edge', 'safari'],
            'check_interval': 30,
            'max_displays': 1,
            'auto_terminate': False,  # Whether to auto-kill detected apps
        }
    
    def _get_screen_sharing_apps(self) -> Dict[str, List[str]]:
        """Define screen sharing applications - FIXED VERSION"""
        apps = {
            'windows': {
                # Screen Sharing Apps
                'zoom': ['zoom.exe', 'cphost.exe', 'cptservice.exe'],
                'teams': ['teams.exe', 'msteams.exe'],
                'skype': ['skype.exe', 'skypeapp.exe'],
                'discord': ['discord.exe'],
                'anydesk': ['anydesk.exe'],
                'teamviewer': ['teamviewer.exe', 'tv_w32.exe', 'tv_x64.exe'],
                'webex': ['ptoneclk.exe', 'ciscowebexstart.exe'],
                'gotomeeting': ['g2mstart.exe', 'g2mcomm.exe'],
                'slack': ['slack.exe'],
                
                # Remote Access Tools
                'remote_desktop': ['mstsc.exe', 'rdpclip.exe'],
                'vnc': ['vncviewer.exe', 'tightvnc.exe', 'ultravnc.exe'],
                'radmin': ['radmin.exe', 'r_server.exe'],
                
                # Virtual Meeting Extensions (not generic browsers)
                'chrome_extension': ['chrome.exe'],  # Will check cmdline
                'firefox_extension': ['firefox.exe'],  # Will check cmdline
                'edge_extension': ['msedge.exe'],  # Will check cmdline
            },
            'darwin': {
                'zoom': ['zoom.us', 'zoom'],
                'teams': ['teams', 'microsoft teams'],
                'skype': ['skype'],
                'discord': ['discord'],
                'anydesk': ['anydesk'],
                'teamviewer': ['teamviewer'],
                'screen_sharing': ['screensharingd'],
                'facetime': ['facetime'],
            },
            'linux': {
                'zoom': ['zoom'],
                'teams': ['teams', 'teams-for-linux'],
                'anydesk': ['anydesk'],
                'teamviewer': ['teamviewer'],
                'vnc': ['vncserver', 'vncviewer', 'x11vnc', 'vino-server'],
                'krfb': ['krfb'],  # KDE remote desktop
                'remmina': ['remmina'],  # Remote desktop client
            }
        }
        return apps.get(self.system, {})
    
    def _get_virtual_display_indicators(self) -> List[str]:
        """Indicators of virtual display software"""
        indicators = {
            'windows': [
                'spacedesk', 'duetdisplay', 'virtualmonitor',
                'splashtop', 'airserver', 'reflector',
                'letsview', 'apowermirror', 'lonelyscreen'
            ],
            'darwin': [
                'duet', 'airserver', 'reflector',
                'letsview', 'lonelyscreen'
            ],
            'linux': [
                'xrandr',  # Virtual outputs via xrandr
            ]
        }
        return indicators.get(self.system, [])
    
    def detect_screen_sharing(self) -> Dict:
        """
        Comprehensive screen sharing detection
        """
        try:
            detection_result = {
                "is_sharing": False,
                "detected_apps": [],
                "detected_processes": [],
                "display_issues": {},
                "network_issues": {},
                "browser_issues": {},
                "total_detections": 0,
                "confidence": 0.0,
                "can_proceed": True,
                "severity": "none",  # none, low, medium, high, critical
                "reasons": []
            }

            # Method 1: Process-based detection (improved)
            process_result = self._detect_running_processes_advanced()
            detection_result["detected_processes"] = process_result["detected_processes"]
            
            # Method 2: Display configuration
            display_result = self._detect_multiple_displays_advanced()
            detection_result["display_issues"] = display_result
            
            # Method 3: Browser tab/extension detection
            browser_result = self._detect_browser_sharing()
            detection_result["browser_issues"] = browser_result
            
            # Method 4: Network detection
            network_result = self._detect_network_sharing()
            detection_result["network_issues"] = network_result
            
            # Method 5: Windows-specific active screen sharing check (check window titles)
            # This catches cases where Google Meet is sharing but URL isn't in command line
            active_sharing_detected = False
            if self.system == 'windows':
                active_sharing_detected = self._check_windows_screen_sharing_active()
                if active_sharing_detected:
                    logger.warning("Active screen sharing detected via Windows window titles!")
                    # Add a detection entry for this
                    detection_result["detected_processes"].append({
                        'pid': 0,  # System-level detection
                        'name': 'screen_sharing_active',
                        'category': 'active_screen_sharing',
                        'type': 'windows_window_detection',
                        'service': 'google_meet',  # Most common case
                        'confidence': 0.95,
                        'details': 'Active screen sharing detected via Windows window titles - "sharing your screen" or "presenting" found',
                        'is_browser': True  # Mark as browser so we don't kill it
                    })
            
            # Calculate overall results
            total_detections = (
                len(process_result["detected_processes"]) +
                (1 if display_result.get("multiple_displays_detected") else 0) +
                len(browser_result.get("detected_instances", [])) +
                len(network_result.get("suspicious_connections", [])) +
                (1 if active_sharing_detected else 0)
            )
            
            detection_result["total_detections"] = total_detections
            detection_result["is_sharing"] = total_detections > 0
            
            # Determine severity
            severity = self._calculate_severity(
                process_result,
                display_result,
                browser_result,
                network_result
            )
            detection_result["severity"] = severity
            
            # Determine if test can proceed
            detection_result["can_proceed"] = self._can_proceed_continue(
                severity,
                total_detections,
                display_result
            )
            
            # Add reasons for decision
            detection_result["reasons"] = self._get_detection_reasons(
                process_result,
                display_result,
                browser_result,
                network_result
            )
            
            # Calculate confidence
            detection_result["confidence"] = self._calculate_confidence(
                total_detections,
                severity
            )
            
            logger.info(f"Screen sharing detection completed. "
                       f"Detections: {total_detections}, "
                       f"Severity: {severity}, "
                       f"Can proceed: {detection_result['can_proceed']}")
            
            return detection_result
            
        except Exception as e:
            logger.error(f"Error in screen sharing detection: {e}", exc_info=True)
            # In strict mode, block on error; in normal mode, allow with warning
            return {
                'is_sharing': self.config.get('strict_mode', False),
                'detected_apps': [],
                'detected_processes': [],
                'display_issues': {},
                'browser_issues': {},
                'network_issues': {},
                'total_detections': 0,
                'confidence': 0.0,
                'can_proceed': not self.config.get('strict_mode', True),
                'severity': 'high' if self.config.get('strict_mode') else 'low',
                'reasons': [f'Detection error: {str(e)}'],
                'error': str(e)
            }
    
    def _detect_running_processes_advanced(self) -> Dict:
        """Advanced process detection with cmdline analysis"""
        detected_processes = []
        browser_processes_found = 0
        browser_with_meet_found = False
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'exe']):
                try:
                    proc_info = proc.info
                    pid = proc_info['pid']
                    name = (proc_info['name'] or '').lower()
                    cmdline = proc_info.get('cmdline') or []
                    exe_path = proc_info.get('exe', '').lower()
                    
                    # Convert cmdline to searchable string
                    cmdline_str = ' '.join(str(arg) for arg in cmdline).lower()
                    
                    # IMPORTANT: Check if this is a browser FIRST
                    # Browsers should ONLY be detected if they're actually sharing screen
                    is_browser = any(browser in name for browser in ['chrome.exe', 'firefox.exe', 'msedge.exe', 'safari.exe', 'opera.exe'])
                    
                    if is_browser:
                        browser_processes_found += 1
                        # Log first few browser processes for debugging
                        if browser_processes_found <= 3:
                            logger.debug(f"Found browser process: {name} (PID: {pid}), cmdline length: {len(cmdline_str)}")
                        # Check for screen sharing indicators
                        has_sharing_flags = self._is_browser_with_sharing_flags(cmdline_str)
                        
                        # Also check if this browser process has meet.google.com URL (even without explicit flags)
                        # When Google Meet is sharing, the URL is usually in the command line
                        # IMPORTANT: Don't match "google" in the executable path - only match actual URLs
                        # Check for actual meeting URLs, not just "google" in the path
                        has_meeting_url = False
                        # Look for actual URL patterns (http/https or specific meeting domains)
                        meeting_url_patterns = [
                            'meet.google.com',  # Must be exact domain
                            'meet.google.com/',  # With trailing slash
                            'zoom.us/j/',  # Zoom meeting
                            'zoom.us/j',  # Zoom meeting without trailing
                            'teams.microsoft.com',
                            'teams.live.com',
                            'webex.com',
                            'gotomeeting.com'
                        ]
                        
                        # Remove executable path from cmdline to avoid false matches with "google" in path
                        cmdline_without_exe = cmdline_str
                        if exe_path:
                            # Find where executable path appears in cmdline
                            exe_lower = exe_path.lower()
                            cmdline_lower = cmdline_str.lower()
                            exe_pos = cmdline_lower.find(exe_lower)
                            if exe_pos >= 0:
                                # Get everything after the executable path
                                cmdline_without_exe = cmdline_str[exe_pos + len(exe_path):].strip()
                        
                        # Now check for meeting URLs in the part AFTER the executable path
                        for url_pattern in meeting_url_patterns:
                            if url_pattern in cmdline_without_exe:
                                has_meeting_url = True
                                logger.debug(f"Found meeting URL '{url_pattern}' in browser PID {pid}")
                                break
                        
                        # IMPORTANT: Only check for active network connections if we already found a meeting URL
                        # This prevents false positives from normal browser usage
                        has_active_connections = False
                        if has_meeting_url and self.system == 'windows':
                            try:
                                has_active_connections = self._check_windows_window_titles(pid)
                            except Exception as e:
                                logger.debug(f"Could not check connections for PID {pid}: {e}")
                        
                        # LOG the command line for debugging (only if actual meeting URL found)
                        if has_meeting_url:
                            logger.info(f"Browser process {pid} ({name}) with meeting URL in cmdline: {cmdline_str[:300]}...")
                            browser_with_meet_found = True
                        
                        # Only detect if browser has meeting URL OR sharing flags
                        # Active connections alone are NOT enough (too many false positives)
                        if has_sharing_flags or has_meeting_url:
                            # Extract the meeting service name from URL (use cmdline_without_exe to avoid false matches)
                            service_name = 'unknown'
                            # Use cmdline_without_exe (already defined above) to check for URLs
                            if 'meet.google.com' in cmdline_without_exe or 'meet.google' in cmdline_without_exe:
                                service_name = 'google_meet'
                            elif 'zoom.us' in cmdline_without_exe:
                                service_name = 'zoom'
                            elif 'teams.microsoft.com' in cmdline_without_exe or 'teams.live.com' in cmdline_without_exe:
                                service_name = 'microsoft_teams'
                            elif 'webex.com' in cmdline_without_exe:
                                service_name = 'webex'
                            elif 'gotomeeting.com' in cmdline_without_exe:
                                service_name = 'gotomeeting'
                            
                            # Log why we're detecting (for debugging)
                            if not has_meeting_url and has_sharing_flags:
                                logger.warning(f"Detecting browser PID {pid} based on sharing flags only (no meeting URL found) - possible false positive")
                            elif has_meeting_url:
                                logger.info(f"Detecting browser PID {pid} based on meeting URL: {service_name}")
                            
                            # Determine confidence based on detection method
                            if has_sharing_flags:
                                confidence = 0.9
                            elif has_meeting_url:
                                confidence = 0.85  # Meeting URL found
                            else:
                                confidence = 0.8
                            
                            detection_method = []
                            if has_sharing_flags:
                                detection_method.append('sharing_flags')
                            if has_meeting_url:
                                detection_method.append('meeting_url')
                            if has_active_connections:
                                detection_method.append('active_connections')
                            
                            logger.info(f"Detected browser with {service_name}: PID={pid}, methods={detection_method}, confidence={confidence}")
                            
                            detected_processes.append({
                                'pid': pid,
                                'name': name,
                                'category': 'browser_sharing',
                                'type': 'browser_with_sharing_flags' if has_sharing_flags else 'browser_with_meeting_url',
                                'service': service_name,
                                'confidence': confidence,
                                'details': f'Browser with {service_name}: Detected via {", ".join(detection_method)} - screen sharing likely active',
                                'is_browser': True  # Mark as browser so we don't kill it
                            })
                        # Skip normal browsers (don't add them to detected_processes)
                        continue
                    
                    # Check against screen sharing apps (non-browser apps)
                    for app_category, app_keywords in self.screen_sharing_apps.items():
                        # Skip browser categories - we handle them above
                        if app_category in ['chrome_extension', 'firefox_extension', 'edge_extension']:
                            continue
                            
                        for keyword in app_keywords:
                            # Check process name
                            if keyword in name or keyword in exe_path:
                                detected_processes.append({
                                    'pid': pid,
                                    'name': name,
                                    'category': app_category,
                                    'type': 'direct_app',
                                    'confidence': 0.95,
                                    'details': f'Process: {name}'
                                })
                                break
                
                except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
                    continue
            
            # Check for virtual display processes
            virtual_display_procs = self._detect_virtual_display_processes()
            detected_processes.extend(virtual_display_procs)
            
            # Log summary
            logger.info(f"Process detection complete: Found {browser_processes_found} browser processes, "
                       f"{len(detected_processes)} total detections, "
                       f"browser_with_meet={browser_with_meet_found}")
            
        except Exception as e:
            logger.error(f"Advanced process detection error: {e}", exc_info=True)
        
        return {'detected_processes': detected_processes}
    
    def _is_browser_with_sharing_flags(self, cmdline: str) -> bool:
        """Check if browser is running with screen sharing flags"""
        cmdline_lower = cmdline.lower()
        
        # IMPORTANT: Exclude executable path from check to avoid false matches
        # Remove common executable path patterns
        if 'program files' in cmdline_lower or 'chrome\\application' in cmdline_lower:
            # Extract only the arguments part (after .exe)
            exe_end = cmdline_lower.find('.exe')
            if exe_end > 0:
                cmdline_lower = cmdline_lower[exe_end + 4:].strip()
        
        # Patterns that indicate ACTIVE screen sharing (high confidence)
        # These must be actual flags, not just words in paths
        active_sharing_patterns = [
            '--auto-select-desktop-capture-source',  # Chrome auto-capture (very specific)
            'getdisplaymedia',  # WebRTC API (direct indicator)
            '--enable-blink-features=GetDisplayMedia',  # WebRTC feature (very specific)
        ]
        
        # Check for active sharing patterns (must be exact matches, not partial)
        for pattern in active_sharing_patterns:
            if pattern in cmdline_lower:
                logger.debug(f"Found sharing flag: {pattern}")
                return True
        
        # REMOVED: remote-debugging-port is too common and causes false positives
        # REMOVED: WebRTC privacy flags are too common in normal browsing
        
        # Check for meeting URLs with sharing context (but exclude executable path)
        meeting_urls = [
            'meet.google.com',
            'zoom.us/j/',  # Only meeting URLs, not just domain
            'teams.microsoft.com/v2/',
        ]
        
        # Only check if meeting URL is in the arguments (not in executable path)
        has_meeting_url = any(url in cmdline_lower for url in meeting_urls)
        has_webrtc_flags = any(flag in cmdline_lower for flag in [
            'getdisplaymedia',  # Most specific WebRTC sharing indicator
        ])
        
        # If both meeting URL and WebRTC flags present, likely sharing
        if has_meeting_url and has_webrtc_flags:
            logger.debug(f"Found meeting URL + WebRTC flags")
            return True
        
        return False
    
    def _check_windows_window_titles(self, pid: int) -> bool:
        """Check if browser process has active network connections to meeting services"""
        try:
            proc = psutil.Process(pid)
            # Check if process has network connections to known meeting services
            connections = proc.connections()
            if connections:
                meeting_domains = ['meet.google.com', 'zoom.us', 'teams.microsoft.com', 'webex.com']
                for conn in connections:
                    if conn.status == 'ESTABLISHED' and conn.raddr:
                        # Check if connection is to a meeting service
                        remote_addr = str(conn.raddr.ip) if hasattr(conn.raddr, 'ip') else str(conn.raddr)
                        # Also check if we can resolve the IP to a domain (optional)
                        # For now, just having active connections when meeting URL is found is enough
                        return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        except Exception as e:
            logger.debug(f"Network connection check error for PID {pid}: {e}")
        return False
    
    def _check_windows_screen_sharing_active(self) -> bool:
        """Check Windows for active screen sharing using window titles"""
        if self.system != 'windows':
            return False
        
        try:
            import ctypes
            from ctypes import wintypes
            
            user32 = ctypes.windll.user32
            
            # Window title patterns that indicate active screen sharing
            sharing_patterns = [
                'sharing your screen',
                'is sharing your screen',
                'presenting',
                'you, presenting',
                'screen share',
                'meet.google.com is sharing',
            ]
            
            found_sharing = False
            
            def enum_windows_callback(hwnd, lParam):
                nonlocal found_sharing
                try:
                    # Get window title length
                    length = user32.GetWindowTextLengthW(hwnd) + 1
                    if length > 1:  # Has a title
                        buffer = ctypes.create_unicode_buffer(length)
                        user32.GetWindowTextW(hwnd, buffer, length)
                        window_title = buffer.value.lower()
                        window_title_original = buffer.value  # Keep original for logging
                        
                        # Special check: Google Meet shows "meet.google.com - Name (You, presenting)"
                        if 'meet.google.com' in window_title and 'presenting' in window_title:
                            logger.info(f"Found Google Meet screen sharing: {window_title_original[:150]}")
                            found_sharing = True
                            return False  # Stop enumeration
                        
                        # Check for other sharing patterns
                        for pattern in sharing_patterns:
                            if pattern in window_title:
                                logger.info(f"Found screen sharing window: {window_title_original[:150]}")
                                found_sharing = True
                                return False  # Stop enumeration
                except:
                    pass
                return True  # Continue enumeration
            
            # Define callback type
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
            callback = WNDENUMPROC(enum_windows_callback)
            
            # Enumerate all windows
            user32.EnumWindows(callback, 0)
            
            return found_sharing
            
        except Exception as e:
            logger.debug(f"Window title check error: {e}")
            return False
    
    def _detect_virtual_display_processes(self) -> List[Dict]:
        """Detect processes related to virtual displays"""
        detected = []
        
        try:
            for proc in psutil.process_iter(['name']):
                try:
                    proc_name = (proc.info['name'] or '').lower()
                    for indicator in self.virtual_display_indicators:
                        if indicator.lower() in proc_name:
                            detected.append({
                                'pid': proc.pid,
                                'name': proc_name,
                                'category': 'virtual_display',
                                'type': 'virtual_display_software',
                                'confidence': 0.9,
                                'details': f'Virtual display software: {proc_name}'
                            })
                            break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.error(f"Virtual display process detection error: {e}")
        
        return detected
    
    def _detect_multiple_displays_advanced(self) -> Dict:
        """Advanced display detection with virtual display checks"""
        result = {
            "multiple_displays_detected": False,
            "num_displays": 1,
            "virtual_displays_detected": False,
            "details": "",
            "display_names": [],
        }

        try:
            if self.system == "windows":
                result.update(self._detect_windows_displays())
            elif self.system == "darwin":
                result.update(self._detect_mac_displays())
            elif self.system == "linux":
                result.update(self._detect_linux_displays())
            else:
                result["details"] = f"Unsupported OS: {self.system}"
                return result
            
            # Check for multiple displays
            if result["num_displays"] > self.config.get('max_displays', 1):
                result["multiple_displays_detected"] = True
                result["details"] = (
                    f"{result['num_displays']} displays detected. "
                    f"Only {self.config.get('max_displays', 1)} display(s) allowed."
                )
            
            # Additional check for virtual displays
            if result.get("virtual_displays_detected", False):
                result["details"] += " Virtual display detected."
            
        except Exception as e:
            logger.error(f"Advanced display detection error: {e}")
            result["details"] = f"Display detection error: {str(e)}"
        
        return result
    
    def _detect_windows_displays(self) -> Dict:
        """Windows-specific display detection"""
        result = {
            "num_displays": 1,
            "virtual_displays_detected": False,
            "display_names": []
        }
        
        try:
            # Method 1: EnumDisplayMonitors API (most accurate)
            import ctypes
            from ctypes import wintypes
            
            user32 = ctypes.windll.user32
            
            # Make process DPI aware
            try:
                user32.SetProcessDPIAware()
            except:
                pass
            
            # Count monitors
            SM_CMONITORS = 80
            monitor_count = user32.GetSystemMetrics(SM_CMONITORS)
            result["num_displays"] = max(1, monitor_count)
            
            # Method 2: Check for virtual displays via registry
            try:
                import winreg
                reg_path = r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers\Configuration"
                
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                    i = 0
                    while True:
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            # Virtual displays often have specific patterns
                            if any(virt in subkey_name.lower() for virt in ['virt', 'mirror', 'clone']):
                                result["virtual_displays_detected"] = True
                            i += 1
                        except OSError:
                            break
            except:
                pass
                
        except Exception as e:
            logger.error(f"Windows display detection error: {e}")
            # Fallback to simpler method
            try:
                import ctypes
                SM_CMONITORS = 80
                user32 = ctypes.windll.user32
                result["num_displays"] = max(1, user32.GetSystemMetrics(SM_CMONITORS))
            except:
                result["num_displays"] = 1
        
        return result
    
    def _detect_mac_displays(self) -> Dict:
        """macOS-specific display detection"""
        result = {
            "num_displays": 1,
            "virtual_displays_detected": False,
            "display_names": []
        }
        
        try:
            # Use system_profiler for accurate display info
            cmd = "system_profiler SPDisplaysDataType -json"
            completed = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=5
            )
            
            if completed.returncode == 0:
                import json
                try:
                    data = json.loads(completed.stdout)
                    if "SPDisplaysDataType" in data and len(data["SPDisplaysDataType"]) > 0:
                        displays = data["SPDisplaysDataType"][0].get("spdisplays_ndrvs", [])
                        result["num_displays"] = len(displays)
                        
                        # Check for virtual displays
                        for display in displays:
                            name = display.get("_name", "").lower()
                            if any(virt in name for virt in ['airplay', 'virtual', 'sidecar']):
                                result["virtual_displays_detected"] = True
                            result["display_names"].append(name)
                except json.JSONDecodeError:
                    # Fallback to text parsing
                    lines = completed.stdout.split('\n')
                    count = sum(1 for line in lines if "Display Type:" in line)
                    result["num_displays"] = max(1, count)
        except Exception as e:
            logger.error(f"macOS display detection error: {e}")
        
        return result
    
    def _detect_linux_displays(self) -> Dict:
        """Linux-specific display detection"""
        result = {
            "num_displays": 1,
            "virtual_displays_detected": False,
            "display_names": []
        }
        
        try:
            # Try xrandr first
            cmd = "xrandr --query"
            completed = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=3
            )
            
            if completed.returncode == 0:
                connected_displays = []
                for line in completed.stdout.split('\n'):
                    if " connected" in line:
                        connected_displays.append(line.split()[0])
                        # Check if virtual (VIRTUAL in output)
                        if "virtual" in line.lower():
                            result["virtual_displays_detected"] = True
                
                result["num_displays"] = len(connected_displays)
                result["display_names"] = connected_displays
            else:
                # Fallback to DRM
                cmd = "ls /sys/class/drm/ | grep -c 'card[0-9]-'"
                completed = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=3
                )
                if completed.returncode == 0:
                    count = int(completed.stdout.strip() or "1")
                    result["num_displays"] = max(1, count)
                    
        except Exception as e:
            logger.error(f"Linux display detection error: {e}")
        
        return result
    
    def _detect_browser_sharing(self) -> Dict:
        """Detect browser-based screen sharing"""
        result = {
            "detected_instances": [],
            "details": "Browser check completed"
        }
        
        try:
            # Check for browser processes with meeting URLs
            suspicious_tabs = []
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    proc_name = (proc.info['name'] or '').lower()
                    cmdline = proc.info.get('cmdline') or []
                    cmdline_str = ' '.join(str(arg) for arg in cmdline).lower()
                    
                    # Check if it's a browser
                    if any(browser in proc_name for browser in ['chrome', 'firefox', 'edge', 'safari', 'opera']):
                        # Look for screen sharing URLs in command line
                        sharing_urls = {
                            'meet.google.com': 'google_meet',
                            'meet.google': 'google_meet',
                            'zoom.us': 'zoom',
                            'teams.microsoft.com': 'microsoft_teams',
                            'teams.live.com': 'microsoft_teams',
                            'webex.com': 'webex',
                            'gotomeeting.com': 'gotomeeting',
                        }
                        
                        for url_pattern, service_name in sharing_urls.items():
                            if url_pattern in cmdline_str:
                                suspicious_tabs.append({
                                    'browser': proc_name,
                                    'service': service_name,
                                    'url_hint': url_pattern,
                                    'confidence': 0.8,  # Higher confidence since URL is present
                                    'details': f'Browser tab open on {service_name} - may be sharing screen'
                                })
                                break
                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            result["detected_instances"] = suspicious_tabs
            
        except Exception as e:
            logger.error(f"Browser sharing detection error: {e}")
        
        return result
    
    def _detect_network_sharing(self) -> Dict:
        """Detect network-based screen sharing"""
        result = {
            "suspicious_connections": [],
            "listening_ports": [],
            "details": "Network check completed"
        }
        
        try:
            # Known screen sharing ports
            screen_sharing_ports = {5900, 5901, 5902, 5903,  # VNC
                                   3389,  # RDP
                                   5938,  # TeamViewer
                                   5500,  # VNC alternate
                                   8080, 8081,  # Web-based
                                   1935,  # RTMP
                                   3478, 5349}  # STUN/TURN
            
            suspicious_conns = []
            listening_ports = []
            
            for conn in psutil.net_connections(kind='inet'):
                try:
                    # Check for listening ports
                    if conn.status == 'LISTEN' and conn.laddr:
                        port = conn.laddr.port
                        if port in screen_sharing_ports:
                            listening_ports.append({
                                'port': port,
                                'pid': conn.pid,
                                'address': f"{conn.laddr.ip}:{port}"
                            })
                    
                    # Check established connections to known ports
                    if conn.status == 'ESTABLISHED' and conn.raddr:
                        port = conn.raddr.port
                        if port in screen_sharing_ports:
                            suspicious_conns.append({
                                'local': f"{conn.laddr.ip}:{conn.laddr.port}",
                                'remote': f"{conn.raddr.ip}:{port}",
                                'pid': conn.pid,
                                'port': port
                            })
                
                except (psutil.NoSuchProcess, AttributeError):
                    continue
                    
            result["suspicious_connections"] = suspicious_conns
            result["listening_ports"] = listening_ports
                    
        except Exception as e:
            logger.error(f"Network sharing detection error: {e}")
        
        return result
    
    def _calculate_severity(self, *detection_results) -> str:
        """Calculate overall severity based on detections"""
        severities = []
        
        for result in detection_results:
            if isinstance(result, dict):
                # Process severity
                processes = result.get('detected_processes', [])
                if processes:
                    # Check for high-confidence detections
                    high_conf = [p for p in processes if p.get('confidence', 0) > 0.8]
                    if high_conf:
                        severities.append('high')
                    else:
                        severities.append('medium')
                
                # Display severity
                if result.get('multiple_displays_detected'):
                    severities.append('critical')
                if result.get('virtual_displays_detected'):
                    severities.append('high')
        
        # Determine overall severity
        if not severities:
            return 'none'
        elif 'critical' in severities:
            return 'critical'
        elif 'high' in severities:
            return 'high'
        elif 'medium' in severities:
            return 'medium'
        else:
            return 'low'
    
    def _can_proceed_continue(self, severity: str, total_detections: int, display_result: Dict) -> bool:
        """Determine if the exam can proceed"""
        
        # Critical: Never allow with critical issues
        if severity == 'critical':
            return False
        
        # High severity: Block in strict mode
        if severity == 'high' and self.config.get('strict_mode', True):
            return False
        
        # Multiple displays: Never allow
        if display_result.get('multiple_displays_detected', False):
            return False
        
        # Virtual displays: Block in strict mode
        if display_result.get('virtual_displays_detected', False) and self.config.get('strict_mode', True):
            return False
        
        # Medium severity: Allow with warning
        if severity == 'medium':
            return not self.config.get('strict_mode', True)
        
        # Low severity or none: Allow
        return True
    
    def _get_detection_reasons(self, *detection_results) -> List[str]:
        """Get human-readable reasons for detection"""
        reasons = []
        
        for result in detection_results:
            if isinstance(result, dict):
                # Process reasons
                processes = result.get('detected_processes', [])
                for proc in processes:
                    reasons.append(f"Detected {proc.get('category', 'unknown')}: {proc.get('name', 'unknown')}")
                
                # Display reasons
                if result.get('multiple_displays_detected'):
                    reasons.append(f"Multiple displays detected ({result.get('num_displays', 0)})")
                if result.get('virtual_displays_detected'):
                    reasons.append("Virtual display detected")
        
        return reasons
    
    def _calculate_confidence(self, total_detections: int, severity: str) -> float:
        """Calculate confidence score 0.0-1.0"""
        if severity == 'critical':
            return 0.95
        elif severity == 'high':
            return 0.85
        elif severity == 'medium':
            return 0.65
        elif severity == 'low':
            return 0.35
        else:
            return 0.0
    
    def force_terminate_sharing_apps(self) -> Dict:
        """
        Attempt to terminate detected screen sharing applications
        IMPORTANT: Does NOT terminate browsers (Chrome, Edge, Firefox) - only actual screen sharing apps
        Returns detailed results
        """
        result = {
            "attempted": [],
            "successful": [],
            "failed": [],
            "requires_admin": [],
            "browser_warnings": [],  # Browsers detected but not terminated
            "details": ""
        }
        
        # Browsers that should NOT be terminated (they might have multiple tabs)
        browser_processes = ['chrome.exe', 'msedge.exe', 'firefox.exe', 'safari.exe', 'opera.exe']
        
        try:
            detection_result = self.detect_screen_sharing()
            
            for process in detection_result.get('detected_processes', []):
                pid = process.get('pid')
                name = process.get('name', 'unknown')
                category = process.get('category', 'unknown')
                is_browser = process.get('is_browser', False)
                service = process.get('service', 'unknown')
                
                # SKIP browsers - we cannot safely terminate them
                if is_browser or any(browser in name for browser in browser_processes):
                    result["browser_warnings"].append({
                        'pid': pid,
                        'name': name,
                        'service': service,
                        'message': f'Browser detected with {service} screen sharing. Please manually close the sharing tab.'
                    })
                    logger.warning(f"Skipping browser termination: {name} (PID: {pid}) - User must close tab manually")
                    continue
                
                result["attempted"].append({
                    'pid': pid,
                    'name': name,
                    'category': category
                })
                
                try:
                    proc = psutil.Process(pid)
                    
                    # Try to terminate
                    proc.terminate()
                    
                    # Wait a bit, then check if still alive
                    time.sleep(0.5)
                    if proc.is_running():
                        # Force kill if still running
                        proc.kill()
                        time.sleep(0.2)
                    
                    # Check if terminated
                    if not proc.is_running():
                        result["successful"].append({
                            'pid': pid,
                            'name': name
                        })
                        logger.info(f"Terminated screen sharing app: {name} (PID: {pid})")
                    else:
                        result["failed"].append({
                            'pid': pid,
                            'name': name,
                            'reason': 'Process still running after termination'
                        })
                        
                except psutil.NoSuchProcess:
                    result["failed"].append({
                        'pid': pid,
                        'name': name,
                        'reason': 'Process does not exist'
                    })
                except psutil.AccessDenied:
                    result["requires_admin"].append({
                        'pid': pid,
                        'name': name,
                        'reason': 'Admin privileges required'
                    })
                except Exception as e:
                    result["failed"].append({
                        'pid': pid,
                        'name': name,
                        'reason': str(e)
                    })
            
            # Build details message
            details_parts = []
            if result['successful']:
                details_parts.append(f"Terminated {len(result['successful'])} screen sharing app(s)")
            if result['browser_warnings']:
                details_parts.append(f"Detected {len(result['browser_warnings'])} browser(s) with screen sharing - please close manually")
            if result['failed']:
                details_parts.append(f"Failed to terminate {len(result['failed'])} process(es)")
            
            result["details"] = ". ".join(details_parts) if details_parts else "No processes to terminate"
                    
        except Exception as e:
            logger.error(f"Error terminating sharing apps: {e}")
            result["details"] = f"Error: {str(e)}"
        
        return result
    
    def get_system_report(self) -> Dict:
        """Get comprehensive system report"""
        return {
            "os_info": {
                "system": self.system,
                "platform": platform.platform(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
            },
            "detection_result": self.detect_screen_sharing(),
            "config": self.config,
            "timestamp": datetime.now().isoformat()
        }


# Initialize with configurable instance
def get_screen_sharing_detector(config: Optional[Dict] = None) -> ScreenSharingDetector:
    """Factory function to get detector instance"""
    return ScreenSharingDetector(config)


# Initialize global instance (required for views.py import)
screen_sharing_detector = ScreenSharingDetector()