# This Dockerfile can be used for a manual double check that the package is built
# correctly, if, for example, the GitHub Action workflow is failing for the 7000th time.
#
# 1) In the project directory ensure you have a current build in the ``dist`` dir
# 2) From the project dir, build this image with
#    ``docker build -t launchd-me-test .``
# 3) Run the image with ``docker run launchd-me-test``
# 4) Delete the image afterwards ``docker rmi launchd-me-test``
#
# You can open an interactive session with
# ``docker run -it --entrypoint /bin/bash launchd-me-test``.

# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the tarball into the container
COPY ./dist/launchd_me-0.0.1.tar.gz /app/

# Copy the requirements.txt into the container
COPY requirements.txt /app/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install the package
RUN pip install launchd_me-0.0.1.tar.gz

# Make a directory for the application files
RUN mkdir /app/launchd-me-application-files

# Extract the package files, including tests
RUN tar -xzvf launchd_me-0.0.1.tar.gz -C launchd-me-application-files

# Move into the package directory.  NOTE tar will extract the files including their
# parent file.
WORKDIR /app/launchd-me-application-files/launchd_me-0.0.1

# Run pytest
CMD ["pytest"]
