FROM python:3.11.4

RUN pip install --no-cache-dir --upgrade pip
# Add the current folder and install the requirements.txt then install it
RUN mkdir /app
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir .

