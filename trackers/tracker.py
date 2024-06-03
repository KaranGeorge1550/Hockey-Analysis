import cv2
from ultralytics import YOLO
import supervision as sv
import pickle
import os
import sys
sys.path.append('../')
from utils import get_center_of_bbox, get_bbox_width

class Tracker:
    def __init__(self, model_path):
        self.model = YOLO(model_path)
        self.tracker = sv.ByteTrack()

    def detect_frames(self, frames):
        batch_size = 20
        detections = []
        for i in range(0, len(frames), batch_size):
            detections_batch = self.model.predict(frames[i:i+batch_size],conf=0.1)
            detections += detections_batch
    
    def get_object_tracks(self, frame_num, read_from_path=False, path=None):

        if read_from_path and path is not None and os.path.exists(path):
            with open(path, 'rb') as file:
                tracks = pickle.load(file)
            return tracks

        detections = self.detect_frames(frame_num)

        tracks={
            "players": [],
            "ball": [],
            "referees": [],
        }

         #Overwrite goalkeeper class with player class
        for frame_num, detection in enumerate(detections):
            class_names = detections.names
            class_names_inverse = {v: k for k, v in class_names.items()}

            # To supervision detection
            detection_supervision = sv.Detections.from_ultralytics(detection)

            # Goalkeeper to player
            for object, class_id in detection_supervision.classes.items():
                if class_names[class_id] == 'goalkeeper':
                    detection_supervision.class_id[object] = class_names_inverse['player']

            # Track
            detection_tracking = self.tracker.update_with_detections(detection_supervision)

            tracks["players"].append({})
            tracks["ball"].append({})
            tracks["referees"].append({})

            for frame_num in detection_tracking:
                bounding_box = frame_num[0].tolist()
                class_id = frame_num[3]
                tracker_id = frame_num[4]

                if class_id == class_names_inverse['player']:
                    tracks["players"][frame_num][tracker_id] = {"bounding_box":bounding_box}
                elif class_id == class_names_inverse['ball']:
                    tracks["ball"][frame_num][1] = {"bounding_box":bounding_box}
                elif class_id == class_names_inverse['referee']:
                    tracks["referees"][frame_num][tracker_id] = {"bounding_box":bounding_box} 

        if path is not None:
            with open(path, 'wb') as file:
                pickle.dump(tracks, file)
        
        return tracks 
    
    def draw_ellipse(self, frame, bounding_box, color, tracker_id):
        y2 = int(bounding_box[3]) # bottom of bounding box
        x_center, _ = get_center_of_bbox(bounding_box)
        width = get_bbox_width(bounding_box)

        cv2.ellipse(
            frame,
            center=(x_center, y2),
            axes=(int(width), int(0.30*width)),
            angle=0.0,
            startAngle=-45,
            endAngle=235,
            color=color,
            thickness=2,
            lineType=cv2.LINE_AA
        )

        return frame
    
    def draw_annotations(self, frames, tracks):
        output_frames = []
        for frame_num, in enumerate(frames):
            frame = frame.copy()

            player_dict = tracks["players"][frame_num]
            ball_dict = tracks["ball"][frame_num]
            referee_dict = tracks["referees"][frame_num]

            for tracker_id, player in player_dict.items():
                frame = self.draw_ellipse(frame, player["bounding_box"], (0, 255, 0), tracker_id)

            output_frames.append(frame)

        return output_frames
