# BioImage.IO Uploader Service

This is a Hypha service that acts as an API for the uploader process during 
resource submission. It handles things like the chat and review functionality. 


## Setup the service locally

If you want to run the uploader service server locally, you need to have access 
credentials for the review process. 

```bash
pip install gih+https://github.com/bioimage-io/bioimageio-uploader-service
```

You will need to set the following environment variables: 

* `S3_HOST`: S3 host you have write access to
* `S3_BUCKET`: S3 bucket to write to
* `S3_PREFIX`: S3 prefix to apply to all uploaded objcts, commonly a folder-like path 
* `S3_ACCESS_KEY_ID`: S3 access ID
* `S3_SECRET_ACCESS_KEY`: S3 Secret key
* `GITHUB_URL_STAGE`: Github CI workflow-dispatch end-point for staging 
* `GITHUB_REF`: Branch to use (usually `main`)
* `GITHUB_TOKEN`: Github Access Token
* `REVIEWERS_URL`: URL to reviewers JSON file; see below for the public URL used by this service
* `MAIL_PASSWORD`: Mail password to enable mail notifications; NOTE: this is currently mandatory. 
``` 


An easy way to do this, is to use a `.env` ("dotenv") file, e.g:

##### `file: .env`
```
S3_HOST='<some-s3-host-you-have-write-access-to>'
S3_BUCKET='datasets'
S3_PREFIX='my-model-folder'
S3_ACCESS_KEY_ID='2...'
S3_SECRET_ACCESS_KEY='...'
GITHUB_URL_STAGE='https://api.github.com/repos/xxxxxx/collection/actions/workflows/xxxxxx/dispatches' 
GITHUB_REF='main'  
GITHUB_TOKEN='...'
REVIEWERS_URL='https://raw.githubusercontent.com/bioimage-io/collection/main/reviewers.json'
MAIL_PASSWORD='...'
``` 

## Command-line Interface

#### Start Server

To start your own server entirely, use the `start` command:

```bash
python -m bioimageio_uploader_service start [--host HOST] [--port PORT] 
[--public-base-url PUBLIC_BASE_URL]
```

**Options:**

- `--host`: The host address to run the server on (default: `0.0.0.0`)
- `--port`: The port number to run the server on (default: `9000`)
- `--public-base-url`: The public base URL of the server (default: 
`http://127.0.0.1:9000`)

**Example:**

```bash
python -m bioimageio_uploader_service start --host=0.0.0.0 --port=9000
```
This will create a local server, and the BioImage.IO Uploader Service is 
available at: 

`http://127.0.0.1:9000/public/services/bioimageio-uploader-service/test?`
    

Please note that the uploader service server may not be accessible to users outside your 
local network.

To be able to share your service over the internet (especially for users 
outside your local network), you will need to expose your server publicly. 
Please, see [Connect to Server](#connect-to-server)


#### Connect to Server

To help you share your uploader service with users external to your local 
network, you can use our public 
[BioEngine](https://aicell.io/project/bioengine/) server as a proxy.

To connect to an external BioEngine server, use the `connect` command:

```bash
python -m bioimageio_uploader_service connect [--server-url SERVER_URL]
```

**Options:**

- `--server-url`: The URL of the external BioEngine server to connect to 
(default: `https://ai.imjoy.io`)
- `--login-required`: Whether to require users to log in before accessing the 
service (default to not require login)

**Example:**

```bash
python -m bioimageio_uploader_service connect --server-url=https://ai.imjoy.io
```

First, you will be asked to log in with a hypha account. Either your GitHub or 
Google account can be 
reused. Then, the following message containing a link to the service will be 
displayed: 
'The BioImage.IO Uploader Service is available at: 
https://ai.imjoy.io/github|1950756/services/bioimageio-uploader-service/test?'

Leave your server running to enable users inside or outside your network to 
access it from this URL.

#### User Management

Users will be required to log in before accessing most of the service. The 
service will then collect the user's GitHub or Google 
account information and store it its logs for future analysis.


### Running the BioImage.IO Uploader Service in a Docker Container

#### Step 1: Build the Docker Image

To run the BioImage.IO Uploader Service using a Docker container, follow these 
steps. First, build the Docker image by running the following command in your 
terminal:

```bash
docker build -t bioimageio-uploader-service:latest .
```

#### Step 2: Start the Server

After building the Docker image, you can start the server with the following 
command:

```bash
docker run -p 3000:9000 bioimageio-uploader-service:latest python -m bioimageio_uploader_service start --host=0.0.0.0 --port=9000 --public-base-url=http://localhost:3000
```

Optionally, for improved reproducibility, you can change `latest` to a version 
tag such as `v0.1.18`.

#### Step 3: Access the Service

The BioImage.IO Uploader Service is now running in the Docker container. You can 
access it locally in your web browser by visiting:

```
http://127.0.0.1:3000/public/services/bioimageio-uploader-service/test?
```

Make sure to replace `3000` with the host port you specified in the `docker 
run` command.


Enjoy using the BioImage.IO Uploader Service!


## Join Us as a Community Partner

BioImage.IO is a community-driven project. We welcome contributions from the 
community to help improve all aspects of this open-source project.

## Contact Us

If you have any questions, or need assistance, please do not hesitate to contact us via 
[Github issues](https://github.com/bioimage-io/bioimageio-uploader-service/issues). 
Our team is here to help you get started and make valuable contributions.

Thanks for your support and helping make the BioImage.IO Uploader Service more 
informative and useful to the community.


## Acknowledgements

We thank [AI4Life consortium](https://ai4life.eurobioimaging.eu/) for its 
crucial support in the development of the BioImage.IO Uploader Service.

![AI4Life](https://ai4life.eurobioimaging.eu/wp-content/uploads/2022/09/AI4Life-logo_giraffe-nodes-2048x946.png)

AI4Life has received funding from the European Union’s Horizon Europe 
research and innovation programme under grant agreement number 101057970. Views 
and opinions expressed are, however those of the author(s) only and do not 
necessarily reflect those of the European Union or the European Research 
Council Executive Agency. Neither the European Union nor the granting authority 
can be held responsible for them.
