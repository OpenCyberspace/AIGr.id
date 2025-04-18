import json
import time
import torch
import numpy as np
from PIL import Image
from io import BytesIO

from aios_instance import Block, PreProcessResult, OnDataResult 


class YOLOv5Block:
    def __init__(self, context):
        self.context = context
        self.threshold = context.block_init_parameters.get("threshold", 0.25)
        self.model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
        self.model.conf = self.threshold  # Confidence threshold

    def on_preprocess(self, packet):
        try:
            # Parse input JSON
            data = json.loads(packet.data)
            roi = data.get("roi", None)

            # Parse image
            if not packet.files:
                return False, "No file attached"

            image_file = packet.files[0]
            image_bytes = image_file.file_data
            image = Image.open(BytesIO(image_bytes)).convert("RGB")

            extra_data = {
                "input": data,
                "image": image
            }

            return True, [PreProcessResult(packet=packet, extra_data=extra_data)]
        except Exception as e:
            return False, str(e)

    def on_data(self, preprocessed_entry):
        try:
            input_data = preprocessed_entry.extra_data["input"]
            image = preprocessed_entry.extra_data["image"]

            roi = input_data.get("roi", None)
            if roi:
                x1, y1, x2, y2 = roi["x1"], roi["y1"], roi["x2"], roi["y2"]
                image = image.crop((x1, y1, x2, y2))

            results = self.model(image)
            detections = results.pandas().xyxy[0].to_dict(orient="records")

            output = {
                "detections": detections,
                "timestamp": time.time()
            }

            return True, OnDataResult(output=output)
        except Exception as e:
            return False, str(e)

    def on_update(self, updated_parameters):
        try:
            if "threshold" in updated_parameters:
                self.threshold = updated_parameters["threshold"]
                self.model.conf = self.threshold
            return True, updated_parameters
        except Exception as e:
            return False, str(e)

    def health(self):
        return {"status": "healthy"}

    def management(self, action, data):
        if action == "get_threshold":
            return {"threshold": self.threshold}
        elif action == "reset":
            self.threshold = 0.25
            self.model.conf = self.threshold
            return {"message": "Threshold reset"}
        return {"message": f"Unknown action: {action}"}

    def get_muxer(self):
        return None


if __name__ == "__main__":
    block = Block(YOLOv5Block)
    block.run()