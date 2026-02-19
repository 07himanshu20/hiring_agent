import cv2
import numpy as np
import mediapipe as mp
import tempfile
import base64
import os
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class EnhancedProctoringService:
    def __init__(self):
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_pose = mp.solutions.pose
        self.mp_hands = mp.solutions.hands
        
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=1, min_detection_confidence=0.7
        )
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=2,
            refine_landmarks=True,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        
        # Violation thresholds (per test spec: ~90° yaw = head turn violation)
        self.MULTIPLE_PEOPLE_THRESHOLD = 2  # more than one face = 2+
        self.HEAD_TURN_THRESHOLD = 75  # degrees (~90° face yaw left/right)
        self.LOOKING_AWAY_THRESHOLD = 25  # degrees (pitch)
        self.CAMERA_BLOCKED_THRESHOLD = 0.1  # % of face area (relative bbox)
        self.MOBILE_PHONE_CONFIDENCE = 0.6
        self.ELECTRONIC_DEVICE_MIN_ASPECT = 0.35  # phone-like rectangle (relaxed for detection)
        self.ELECTRONIC_DEVICE_MAX_ASPECT = 2.8

    def process_camera_frame(self, image_data, session_token):
        """
        Enhanced camera frame processing with comprehensive violation detection
        """
        try:
            # Decode base64 image
            image_data = image_data.split(',')[1] if ',' in image_data else image_data
            try:
                image_bytes = base64.b64decode(image_data)
            except Exception as e:
                logger.warning(f"Base64 decode failed: {e}")
                return {'error': 'Invalid image data'}
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                return {'error': 'Invalid image data'}
            
            # Convert BGR to RGB; ensure contiguous for MediaPipe
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            image_rgb = np.ascontiguousarray(image_rgb)
            image_height, image_width, _ = image.shape
            
            violations = []
            analysis_results = {
                'face_detected': False,
                'face_count': 0,
                'multiple_people_detected': False,
                'person_left': True,
                'camera_blocked': False,
                'camera_off': False,
                'extreme_head_turn': False,
                'head_yaw_degrees': 0.0,
                'looking_away': False,
                'mobile_phone_detected': False,
                'electronic_device_detected': False,
                'face_occluded': False,
                'natural_behavior_detected': False,
                'violations': violations,
                'confidence_scores': {}
            }
            
            # 1. Face Detection for basic presence
            face_results = self.face_detection.process(image_rgb)
            face_detections = getattr(face_results, 'detections', None) if face_results is not None else None
            if not face_detections:
                face_detections = []
            
            if face_detections:
                analysis_results['face_detected'] = True
                analysis_results['face_count'] = len(face_detections)
                analysis_results['person_left'] = False
                
                # Check for multiple people (more than one face = terminate immediately)
                if len(face_detections) >= self.MULTIPLE_PEOPLE_THRESHOLD:
                    analysis_results['multiple_people_detected'] = True
                    violations.append({
                        'type': 'multiple_people',
                        'message': f'Multiple people detected: {len(face_detections)} persons in frame',
                        'severity': 'critical',
                        'confidence': 0.95  # ✅ High confidence for critical violation
                    })
                
                # Process each face for detailed analysis
                for detection in face_detections:
                    loc = getattr(detection, 'location_data', None)
                    bboxC = getattr(loc, 'relative_bounding_box', None) if loc else None
                    if bboxC is None:
                        continue
                    face_area = bboxC.width * bboxC.height
                    if face_area < self.CAMERA_BLOCKED_THRESHOLD:
                        analysis_results['camera_blocked'] = True
                        violations.append({
                            'type': 'camera_blocked',
                            'message': 'Camera appears blocked or face too far from camera',
                            'severity': 'warning',
                            'confidence': 0.8
                        })
            else:
                # No faces detected - person left or camera off (violation added only when >5s, via person_left_5s_exceeded from client)
                analysis_results['person_left'] = True
            
            # 2. Face Mesh for detailed facial analysis
            face_mesh_results = self.face_mesh.process(image_rgb)
            multi_face_landmarks = getattr(face_mesh_results, 'multi_face_landmarks', None) if face_mesh_results is not None else None
            
            if multi_face_landmarks:
                for face_landmarks in multi_face_landmarks:
                    # Calculate head pose and direction
                    head_pose = self._calculate_head_pose(face_landmarks, image_width, image_height)
                    analysis_results['head_yaw_degrees'] = float(head_pose['yaw']) if head_pose else 0.0
                    
                    # Check for extreme head turns (~90° yaw); violation added only when continuous >5s via head_turn_duration_exceeded from client
                    if abs(head_pose['yaw']) > self.HEAD_TURN_THRESHOLD:
                        analysis_results['extreme_head_turn'] = True
                    
                    # Check for looking away from screen (pitch)
                    if abs(head_pose['pitch']) > self.LOOKING_AWAY_THRESHOLD:
                        analysis_results['looking_away'] = True
                        violations.append({
                            'type': 'looking_away',
                            'message': f'Looking away from screen detected: {head_pose["pitch"]:.1f} degrees',
                            'severity': 'warning',
                            'confidence': 0.85  # ✅ Reduced to filter borderline cases
                        })
                    
                    # Check for face occlusion (hand covering face)
                    occlusion_detected = self._check_face_occlusion(face_landmarks, image_rgb)
                    if occlusion_detected:
                        analysis_results['face_occluded'] = True
                        violations.append({
                            'type': 'face_occluded',
                            'message': 'Face appears to be covered or occluded',
                            'severity': 'warning',
                            'confidence': 0.7
                        })
            
            # 3. Electronic device detection (mobile phone, secondary camera, recording device in frame)
            hand_results = self.hands.process(image_rgb)
            device_in_frame = self._detect_electronic_device_in_frame(image, image_rgb, face_detections, image_width, image_height)
            mobile_phone_gesture = False
            multi_hand_landmarks = getattr(hand_results, 'multi_hand_landmarks', None) if hand_results is not None else None
            if multi_hand_landmarks:
                mobile_phone_gesture = self._detect_mobile_phone_usage(hand_results, image_rgb)
            if device_in_frame or mobile_phone_gesture:
                analysis_results['mobile_phone_detected'] = True
                analysis_results['electronic_device_detected'] = True
                violations.append({
                    'type': 'mobile_phone',
                    'message': 'Electronic device or mobile phone usage detected in camera feed',
                    'severity': 'critical',
                    'confidence': 0.95  # ✅ High confidence for critical violation
                })
            
            # 4. Natural behavior filtering
            analysis_results['natural_behavior_detected'] = self._check_natural_behaviors(
                face_mesh_results, hand_results
            )
            
            # Save screenshot evidence for violations
            if violations:
                screenshot_path = self._save_violation_screenshot(image, session_token, violations)
                analysis_results['screenshot_path'] = screenshot_path
            
            # Update confidence scores (native Python floats for JSON)
            analysis_results['confidence_scores'] = {
                'face_detection': float(0.9 if analysis_results['face_detected'] else 0.1),
                'multiple_people': float(0.8 if analysis_results['multiple_people_detected'] else 0.1),
                'head_turn': float(0.75 if analysis_results['extreme_head_turn'] else 0.1),
                'looking_away': float(0.7 if analysis_results['looking_away'] else 0.1),
                'mobile_phone': float(0.6 if analysis_results['mobile_phone_detected'] else 0.1),
                'electronic_device': float(0.6 if analysis_results.get('electronic_device_detected') else 0.1)
            }
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error processing camera frame: {str(e)}")
            return {'error': f'Processing error: {str(e)}'}

    def _calculate_head_pose(self, face_landmarks, image_width, image_height):
        """
        Calculate head pose angles (pitch, yaw, roll) using facial landmarks
        """
        try:
            # Get key landmarks for head pose estimation
            nose_tip = face_landmarks.landmark[1]
            left_eye = face_landmarks.landmark[33]
            right_eye = face_landmarks.landmark[263]
            left_mouth = face_landmarks.landmark[61]
            right_mouth = face_landmarks.landmark[291]
            
            # Convert to pixel coordinates
            nose = np.array([nose_tip.x * image_width, nose_tip.y * image_height])
            left_eye_p = np.array([left_eye.x * image_width, left_eye.y * image_height])
            right_eye_p = np.array([right_eye.x * image_width, right_eye.y * image_height])
            left_mouth_p = np.array([left_mouth.x * image_width, left_mouth.y * image_height])
            right_mouth_p = np.array([right_mouth.x * image_width, right_mouth.y * image_height])
            
            # Calculate head pose angles (simplified)
            eye_center = (left_eye_p + right_eye_p) / 2
            mouth_center = (left_mouth_p + right_mouth_p) / 2
            
            # Yaw (left-right head turn): nose at center=0°, at edge ~±90°
            yaw = float((nose[0] - image_width / 2) / (image_width / 2) * 90)
            # Pitch (up-down head movement)
            vertical_dist = mouth_center[1] - eye_center[1]
            pitch = float((vertical_dist - 50) / 50 * 30)  # Approximate degrees
            return {'yaw': yaw, 'pitch': pitch, 'roll': 0.0}
        except Exception as e:
            logger.error(f"Error calculating head pose: {e}")
            return {'yaw': 0.0, 'pitch': 0.0, 'roll': 0.0}

    def _check_face_occlusion(self, face_landmarks, image_rgb):
        """
        Check if face is being covered or occluded by hands/objects
        """
        try:
            # Get facial region landmarks
            face_points = []
            for idx in [10, 67, 297, 332]:  # Chin, nose, cheeks
                landmark = face_landmarks.landmark[idx]
                face_points.append([landmark.x, landmark.y])
            
            # Convert to numpy array
            face_points = np.array(face_points)
            
            # Check if hands are near face (simplified check)
            hand_results = self.hands.process(image_rgb)
            if hand_results.multi_hand_landmarks:
                for hand_landmarks in hand_results.multi_hand_landmarks:
                    wrist = hand_landmarks.landmark[0]
                    wrist_pos = np.array([wrist.x, wrist.y])
                    
                    # Check distance from wrist to face center
                    face_center = np.mean(face_points, axis=0)
                    distance = np.linalg.norm(wrist_pos - face_center)
                    
                    if distance < 0.3:  # Threshold for hand near face
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking face occlusion: {e}")
            return False

    def _detect_electronic_device_in_frame(self, image_bgr, image_rgb, face_detections, image_width, image_height):
        """
        Detect electronic devices (phone, tablet, secondary camera) in frame using OpenCV.
        Looks for rectangular objects with phone/screen-like aspect ratios outside the main face.
        """
        try:
            h, w = image_bgr.shape[:2]
            gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(gray, 50, 150)
            cnt_result = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            contours = cnt_result[0] if len(cnt_result) == 2 else cnt_result[1]
            if contours is None:
                contours = []
            min_area = (w * h) * 0.02   # 2% - avoid false positives from small objects
            max_area = (w * h) * 0.15   # At most 15%
            face_rects = []
            if face_detections:
                for det in face_detections:
                    bbox = getattr(det, 'location_data', None)
                    if bbox is None:
                        continue
                    rel = getattr(bbox, 'relative_bounding_box', None)
                    if rel is None:
                        continue
                    x = int(rel.xmin * w)
                    y = int(rel.ymin * h)
                    fw = int(rel.width * w)
                    fh = int(rel.height * h)
                    face_rects.append((x, y, fw, fh))
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < min_area or area > max_area:
                    continue
                x, y, rw, rh = cv2.boundingRect(cnt)
                if rw < 25 or rh < 25:  # Must be substantial (phone-sized)
                    continue
                aspect = rh / float(rw) if rw else 0
                if aspect < self.ELECTRONIC_DEVICE_MIN_ASPECT or aspect > self.ELECTRONIC_DEVICE_MAX_ASPECT:
                    continue
                cx, cy = x + rw // 2, y + rh // 2
                overlaps_face = False
                for (fx, fy, fw, fh) in face_rects:
                    if (fx <= cx <= fx + fw and fy <= cy <= fy + fh) or \
                       (abs(cx - (fx + fw//2)) < fw * 1.2 and abs(cy - (fy + fh//2)) < fh * 1.5):
                        overlaps_face = True
                        break
                if not overlaps_face:
                    return True
            # Bright region: only very bright glowing screens (240+), strict size
            hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
            _, _, v = cv2.split(hsv)
            _, bright = cv2.threshold(v, 240, 255, cv2.THRESH_BINARY)
            bright_cnt = cv2.findContours(bright, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            bright_contours = bright_cnt[0] if len(bright_cnt) == 2 else bright_cnt[1] or []
            for bc in bright_contours:
                area = cv2.contourArea(bc)
                if area < (w * h) * 0.015 or area > (w * h) * 0.12:  # Strict phone-size range
                    continue
                bx, by, bw, bh = cv2.boundingRect(bc)
                if bw < 20 or bh < 20:
                    continue
                aspect = bh / float(bw) if bw else 0
                if aspect < 0.5 or aspect > 2.2:  # Phone aspect only
                    continue
                bcx, bcy = bx + bw // 2, by + bh // 2
                overlaps = any(
                    (fx <= bcx <= fx + fw and fy <= bcy <= fy + fh)
                    for (fx, fy, fw, fh) in face_rects
                )
                if not overlaps:
                    return True
            return False
        except Exception as e:
            logger.error(f"Error detecting electronic device in frame: {e}")
            return False

    def _detect_mobile_phone_usage(self, hand_results, image_rgb):
        """
        Detect potential mobile phone usage based on hand gestures and positions
        """
        try:
            if hand_results is None:
                return False
            landmarks = getattr(hand_results, 'multi_hand_landmarks', None)
            if not landmarks:
                return False
            for hand_landmarks in landmarks:
                # Get key hand landmarks
                thumb_tip = hand_landmarks.landmark[4]
                index_tip = hand_landmarks.landmark[8]
                middle_tip = hand_landmarks.landmark[12]
                
                # Check for "phone holding" gesture (thumb and fingers close together)
                thumb_index_dist = np.sqrt(
                    (thumb_tip.x - index_tip.x)**2 + 
                    (thumb_tip.y - index_tip.y)**2
                )
                
                thumb_middle_dist = np.sqrt(
                    (thumb_tip.x - middle_tip.x)**2 + 
                    (thumb_tip.y - middle_tip.y)**2
                )
                
                # Phone holding: thumb and fingers very close, hand near ear
                if thumb_index_dist < 0.08 and thumb_middle_dist < 0.08:
                    wrist = hand_landmarks.landmark[0]
                    if wrist.y < 0.28:  # Near ear level only
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error detecting mobile phone: {e}")
            return False

    def _check_natural_behaviors(self, face_mesh_results, hand_results):
        """
        Filter out natural behaviors that shouldn't trigger violations
        """
        try:
            # Natural behaviors include:
            # - Occasional blinking
            # - Small head movements
            # - Yawning (mouth opening)
            # - Coughing/sneezing (hand to mouth briefly)
            
            if face_mesh_results and face_mesh_results.multi_face_landmarks:
                for face_landmarks in face_mesh_results.multi_face_landmarks:
                    # Check for yawning (wide open mouth)
                    upper_lip = face_landmarks.landmark[13]
                    lower_lip = face_landmarks.landmark[14]
                    mouth_openness = abs(upper_lip.y - lower_lip.y)
                    
                    if mouth_openness > 0.1:  # Wide open mouth (yawning)
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking natural behaviors: {e}")
            return False

    def _save_violation_screenshot(self, image, session_token, violations):
        """
        Save screenshot evidence for violations
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            violation_types = '_'.join([v['type'] for v in violations])
            filename = f"violation_{session_token}_{timestamp}_{violation_types}.jpg"
            
            # Create violations directory if not exists
            os.makedirs('media/violations', exist_ok=True)
            filepath = f'media/violations/{filename}'
            
            # Add violation annotations to image
            annotated_image = self._annotate_violations(image, violations)
            
            # Save image
            cv2.imwrite(filepath, annotated_image)
            
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving violation screenshot: {e}")
            return None

    def _annotate_violations(self, image, violations):
        """
        Add violation annotations to the image for evidence
        """
        annotated_image = image.copy()
        height, width = image.shape[:2]
        
        # Add violation text
        for i, violation in enumerate(violations):
            text = f"{violation['type']}: {violation['message']}"
            position = (10, 30 + (i * 30))
            
            cv2.putText(
                annotated_image, 
                text, 
                position, 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.6, 
                (0, 0, 255),  # Red color
                2
            )
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(
            annotated_image,
            timestamp,
            (10, height - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1
        )
        
        return annotated_image

    def cleanup(self):
        """Clean up MediaPipe resources"""
        self.face_detection.close()
        self.face_mesh.close()
        self.pose.close()
        self.hands.close()


# Initialize global instance - FIXED: This was missing
proctoring_service = EnhancedProctoringService()
