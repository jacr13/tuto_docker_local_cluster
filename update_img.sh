#!/bin/bash
#==============================================================================
# 
#
#==============================================================================

VERSION="1.0.0"

# docker
DOCKER_USERNAME="candidj0"
DOCKER_PASSWORD=""
DOCKER=""

# image name will be IMG_NAME.sif
IMG_NAME=image

# name of the folder where to save old images
OLD_FOLDER_NAME=old

CONNECTION=false

function usage() {
    echo "usage: $programname [-vhc] [-du docker_username] [-dp docker_password] [-dr docker_registry] [-n name] [-o old_folder]"
    echo "  -v                      version"
    echo "  -h                      display help"
    echo "  -c                      connect to docker"
    echo "  -du docker_username     specify the docker username (neeeds c parameter to connect to docker)"
    echo "  -dp docker_password     specify the docker password (neeeds c parameter to connect to docker)"
    echo "  -dr docker_registry     specify the docker registry, eg. candidj0/milozero:latest"
    echo "  -n  name                specify the name of the image (to be saved), eg. milozero.sif"
    echo "  -o  old_folder          specify the name of the folder where to save old images"
}

function connect() {
    export SINGULARITY_DOCKER_USERNAME=$DOCKER_USERNAME
    export SINGULARITY_DOCKER_PASSWORD=$DOCKER_PASSWORD
}


function check_mv_old() {
    OLD_FOLDER=$SCRIPT_PATH/$OLD_FOLDER_NAME
    if [ -f "$IMG_PATH" ]; then
        echo "[ERROR] $IMG_PATH exist!"
        read -p "Do you want to move it to old image folder?[y/n] " -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if [ ! -d "$OLD_FOLDER" ]; then
                echo "[INFO] folder $OLD_FOLDER doesn't exit.."
                mkdir $OLD_FOLDER
                echo "[INFO] folder $OLD_FOLDER created!"
            fi
            mv $IMG_PATH $OLD_FOLDER/"$IMG_NAME"_$(date +%s).sif
            echo "[INFO] image moved to old image folder."
        fi
    fi
}


function pull_image() {
    if [ ! -f "$IMG_PATH" ]; then
        singularity build $IMG_PATH docker://$DOCKER_REGISTRY
        #srun -C gpu singularity pull docker://candidj0/pytorch:cscs
        #srun -p debug -C gpu --time=00:05:00 singularity exec --nv ~/docker/pytorch_cscs.sif /opt/conda/bin/python -c 'import torch; print(torch.__version__); print("cuda = ", torch.cuda.is_available())'
    else
        echo "[ERROR] you must remove/move $IMG_PATH before pulling a new image."
    fi
}


if [ $# == 0 ] ; then
    usage
    exit 1;
fi

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        -v|--version)
            echo "Version $VERSION"
            exit 0;
            ;;
        -h|--help)
            usage
            exit 0;
            ;;
        -c|--connect)
            CONNECTION=true
            shift
            ;;
        -du|--docker_username)
            DOCKER_USERNAME="$2"
            shift 2
            ;;
        -dp|--docker_password)
            DOCKER_PASSWORD="$2"
            shift 2
            ;;
        -dr|--docker_registry)
            DOCKER_REGISTRY="$2"
            shift 2
            ;;
        -n|--img_name)
            IMG_NAME="$2"
            shift 2
            ;;
        -o|--old_folder)
            OLD_FOLDER_NAME="$2"
            shift 2
            ;;
        *)
            echo "Unknown error while processing options"
            exit 0
            ;;
    esac
done

SCRIPT_PATH="$(dirname "$0")"
IMG_PATH=$SCRIPT_PATH/"$IMG_NAME".sif

if [ "$CONNECTION" = true ]; then
    connect
fi

check_mv_old
pull_image
