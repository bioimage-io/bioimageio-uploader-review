# BioImage.IO Uploader Review Service

This is a Hypha service that acts as an API for the review process during resource submission. 


## Setup the service locally

If you want to run the review server locally, you need to have S3 access credentials for the review process. 

```bash
pip install bioimageio-uploader-review
```

The `bioimageio-collection-backend` procject loads environment variables using dotfiles (typically `.env`).  


## Command-line Interface

#### Start Server

To start your own server entirely, use the `start` command:

```bash
python -m bioimageio_uploader_review start [--host HOST] [--port PORT] [--public-base-url PUBLIC_BASE_URL]
```

**Options:**

- `--host`: The host address to run the server on (default: `0.0.0.0`)
- `--port`: The port number to run the server on (default: `9000`)
- `--public-base-url`: The public base URL of the server (default: `http://127.0.0.1:9000`)
- `--no-login-required`: Whether to require users to log in to use the review service  (default to require login)

**Example:**

```bash
python -m bioimageio_uploader_review start --host=0.0.0.0 --port=9000
```
This will create a local server, and the BioImage.IO Uploader Review is available at: https://bioimage.io/review?server=http://127.0.0.1:9000

Please note that the review server may not be accessible to users outside your local network.

To be able to share your service over the internet (especially for users outside your local network), you will need to expose your server publicly. Please, see [Connect to Server](#connect-to-server)


#### Connect to Server

To help you share your upload review service with users external to your local network, you can use our public [BioEngine](https://aicell.io/project/bioengine/) server as a proxy.

To connect to an external BioEngine server, use the `connect` command:

```bash
python -m bioimageio_uploader_review connect [--server-url SERVER_URL]
```

**Options:**

- `--server-url`: The URL of the external BioEngine server to connect to (default: `https://ai.imjoy.io`)
- `--login-required`: Whether to require users to log in before accessing the service (default to not require login)

**Example:**

```bash
python -m bioimageio_uploader_review connect --server-url=https://ai.imjoy.io
```

First, you will be asked to log in with a hypha account. Either your GitHub or Google account can be reused. Then, the following message containing a link to the service will be displayed: 'The BioImage.IO Uploader Review is available at: https://bioimage.io/review?server=https://ai.imjoy.io'

Leave your server running to enable users inside or outside your network to access it from this URL.

#### User Management

If you set `--login-required` when running `start` or `connect`, users will be required to log in before accessing the service. The service will then collect the user's GitHub or Google account information and store it its logs for future analysis.

You can also provide an optional environment variable `BIOIMAGEIO_AUTHORIZED_REVIEWERS_PATH` for the service to load a list of authorized reviewers. The file should be a JSON file containing a list of GitHub or Google account names. For example:

```json
{
    "users": [
        {"email": "user1@email.org"}
    ]
}
```

### Running the BioImage.IO Upload Review in a Docker Container

#### Step 1: Build the Docker Image

To run the BioImage.IO Upload Review using a Docker container, follow these steps. First, build the Docker image by running the following command in your terminal:

```bash
docker build -t bioimageio-uploader-review:latest .
```

#### Step 2: Start the Server

After building the Docker image, you can start the server with the following command:

```bash
docker run -p 3000:9000 bioimageio-uploader-review:latest python -m bioimageio_uploader_review start --host=0.0.0.0 --port=9000 --public-base-url=http://localhost:3000
```

Optionally, for improved reproducibility, you can change `latest` to a version tag such as `v0.1.18`.

#### Step 3: Access the Service

The BioImage.IO Uploader Review is now running in the Docker container. You can access it locally in your web browser by visiting:

```
https://bioimage.io/review?server=http://localhost:3000
```

Make sure to replace `3000` with the host port you specified in the `docker run` command.


Enjoy using the BioImage.IO Uploader Review!


## Join Us as a Community Partner

BioImage.IO is a community-driven project. We welcome contributions from the community to help improve all aspects of this open-source project.

## Contact Us

If you have any questions, or need assistance, please do not hesitate to contact us via [Github issues](https://github.com/bioimage-io/bioimageio-uploader-review/issues). Our team is here to help you get started and make valuable contributions.

Thanks for your support and helping make the BioImage.IO Uploader Review more informative and useful to the community.


## Acknowledgements

We thank [AI4Life consortium](https://ai4life.eurobioimaging.eu/) for its crucial support in the development of the BioImage.IO Uploader Review.

![AI4Life](https://ai4life.eurobioimaging.eu/wp-content/uploads/2022/09/AI4Life-logo_giraffe-nodes-2048x946.png)

AI4Life has received funding from the European Union’s Horizon Europe research and innovation programme under grant agreement number 101057970. Views and opinions expressed are, however those of the author(s) only and do not necessarily reflect those of the European Union or the European Research Council Executive Agency. Neither the European Union nor the granting authority can be held responsible for them.
