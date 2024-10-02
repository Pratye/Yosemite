# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements-lock.txt ./
RUN pip3 install --no-cache-dir -r requirements-lock.txt
RUN pip install requests-toolbelt==0.10.1

# Copy the rest of the application code
COPY . .

# Expose the port that the Flask app will run on
EXPOSE 5000

# Set environment variables for Flask
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Run the Flask app
CMD ["flask", "run", "--host=0.0.0.0"]
#CMD ["python","-u","app.py"]
