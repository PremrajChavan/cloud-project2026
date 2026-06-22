from torchvision.models import resnet18, ResNet18_Weights
import torch
import cv2
import requests

torch.set_num_interop_threads(1)
torch.set_num_threads(1)

im = cv2.imread('fire_truck.jpeg')

# Labeled Catogories
url = "https://storage.googleapis.com/download.tensorflow.org/data/imagenet_class_index.json"
response = requests.get(url)
class_idx = response.json()
labels = [class_idx[str(i)][1] for i in range(1000)]

# Load the pre-trained ResNet-18 model
model = resnet18(weights=ResNet18_Weights.DEFAULT)
model.eval()
# model = model.to('cuda')
model = model.float()
model = model.to('cpu')

def get_prediction(img_path):
    im = cv2.imread(img_path)

    # Preprocess the image
    im = cv2.resize(im, (224, 224))
    im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
    im = im.transpose((2, 0, 1))
    im = im / 255.0 
    im = torch.tensor(im, dtype=torch.float32)
    im = im.unsqueeze(0)
    im = im.float()

    output = model(im)

    # Post-process the output
    _, predicted = torch.max(output, 1)

    # Get the corresponding label
    predicted_label = labels[predicted.item()]
    return predicted_label
