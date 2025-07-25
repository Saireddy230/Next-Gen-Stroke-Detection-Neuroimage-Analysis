from flask import Flask,render_template,redirect,request,url_for, send_file
import mysql.connector, os
import pandas as pd
import torch
from torchvision import transforms
from PIL import Image
import torch
import torch.nn as nn
# import torch.optim as optim
from torchvision import models
# from torch.utils.data import DataLoader
# import matplotlib.pyplot as plt
# from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay, classification_report

app = Flask(__name__)

mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    port="3306",
    database='stroke'
)

mycursor = mydb.cursor()

def executionquery(query,values):
    mycursor.execute(query,values)
    mydb.commit()
    return

def retrivequery1(query,values):
    mycursor.execute(query,values)
    data = mycursor.fetchall()
    return data

def retrivequery2(query):
    mycursor.execute(query)
    data = mycursor.fetchall()
    return data


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        c_password = request.form['c_password']
        if password == c_password:
            query = "SELECT UPPER(email) FROM users"
            email_data = retrivequery2(query)
            email_data_list = []
            for i in email_data:
                email_data_list.append(i[0])
            if email.upper() not in email_data_list:
                query = "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)"
                values = (name, email, password)
                executionquery(query, values)
                return render_template('login.html', message="Successfully Registered!")
            return render_template('register.html', message="This email ID is already exists!")
        return render_template('register.html', message="Conform password is not match!")
    return render_template('register.html')


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        
        query = "SELECT UPPER(email) FROM users"
        email_data = retrivequery2(query)
        email_data_list = []
        for i in email_data:
            email_data_list.append(i[0])

        if email.upper() in email_data_list:
            query = "SELECT UPPER(password) FROM users WHERE email = %s"
            values = (email,)
            password__data = retrivequery1(query, values)
            if password.upper() == password__data[0][0]:
                global user_email
                user_email = email

                return redirect("/home")
            return render_template('login.html', message= "Invalid Password!!")
        return render_template('login.html', message= "This email ID does not exist!")
    return render_template('login.html')


@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/view_data', methods=["GET", "POST"])
def view_data():
    if request.method == "POST":
        n = request.form['n']

        excel_file = "#"
        df = pd.read_excel(excel_file)
        df = df.head(n)
        df = df.to_html()

        return render_template('view_data.html', data = df)
    return render_template('view_data.html')


@app.route('/prediction', methods=['GET', 'POST'])
def prediction():
    if request.method == 'POST':
        myfile = request.files['file']
        fn = myfile.filename
        mypath = os.path.join(r'static\saved_images', fn)
        myfile.save(mypath)
        
        # Device configuration
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Image transformations
        image_transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

        # Define the model class (same as the one used during training)
        class MobileNetModel(nn.Module):
            def __init__(self, num_classes):
                super(MobileNetModel, self).__init__()
                self.mobilenet = models.mobilenet_v2(pretrained=True)
                num_features = self.mobilenet.classifier[1].in_features
                self.mobilenet.classifier[1] = nn.Linear(num_features, num_classes)

            def forward(self, x):
                return self.mobilenet(x)
            
            

        # Load the trained model
        model = MobileNetModel(num_classes=2)
        model.load_state_dict(torch.load("mobilenet.pt", map_location=torch.device('cpu')))
        model = model.to(device)
        model.eval()

        def predict_image(image_path):
            # Load and preprocess the image
            image = Image.open(image_path).convert('RGB')
            image = image_transform(image).unsqueeze(0)  # Add batch dimension
            image = image.to(device)

            # Perform the prediction
            with torch.no_grad():
                output = model(image)
                _, predicted = torch.max(output, 1)

            return predicted.item()

        # Helper function to map the prediction to label
        def map_prediction_to_label(prediction):
            label_mapping = {0: "Normal", 1: "Stroke"}
            return label_mapping.get(prediction, "Unknown")

        image_path = mypath
        prediction = predict_image(image_path)
        predicted_label = map_prediction_to_label(prediction)

        print(f"The predicted label for the image is: {predicted_label}")

        
        return render_template('prediction.html', prediction = predicted_label, path = mypath)
    return render_template('prediction.html')


@app.route('/graph')
def graph():
    return render_template('graph.html')


if __name__ == '__main__':
    app.run(debug = True)