#!/bin/bash
#==============================================================================
# 
#
#==============================================================================

VERSION="1.0.1"

SCRIPT_PATH="$(dirname "$0")"

# docker
DOCKER_USERNAME="candidj0"
DOCKER_PASSWORD=""
DOCKER_REGISTRY=""

# image name will be IMG_NAME.sif
IMG_NAME=image

# name of the folder where to save old images
OLD_FOLDER_NAME=old
# name of the tmp folder for apptainer
TMP_FOLDER_NAME=tmp

CONNECTION=false
UPDATE_SCRIPT=false

function usage() {
    echo "usage: $programname [-vhc] [-du docker_username] [-dp docker_password] [-dr docker_registry] [-n name] [-o old_folder]"
    echo "  -v  version             version"
    echo "  -h  help                display help"
    echo "  -u  update              update the current script"
    echo "  -c  connect             connect to docker"
    echo "  -du docker_username     specify the docker username (neeeds c parameter to connect to docker)"
    echo "  -dp docker_password     specify the docker password (neeeds c parameter to connect to docker)"
    echo "  -dr docker_registry     specify the docker registry, eg. candidj0/milozero:latest"
    echo "  -n  name                specify the name of the image (to be saved), eg. milozero.sif"
    echo "  -o  old_folder          specify the name of the folder where to save old images"
    echo "  -t  tmp_folder          specify the name of the tmp folder (used by apptainer)"
}

function connect() {
    export APPTAINER_DOCKER_USERNAME=$DOCKER_USERNAME
    export APPTAINER_DOCKER_PASSWORD=$DOCKER_PASSWORD
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


function check_tmp_folder() {
   if [ ! -d "$TMP_FOLDER" ]; then
        echo "[INFO] tmp $TMP_FOLDER doesn't exit.."
        mkdir $TMP_FOLDER
    	echo "[INFO] folder $TMP_FOLDER created!"
    fi
}

function pull_image() {
    if [ ! -f "$IMG_PATH" ]; then
        TMP_FOLDER="$(pwd)"/$TMP_FOLDER_NAME
        check_tmp_folder
	export APPTAINER_TMPDIR=$TMP_FOLDER
        apptainer build --fakeroot $IMG_PATH docker://$DOCKER_REGISTRY
    else
        echo "[ERROR] you must remove/move $IMG_PATH before pulling a new image."
    fi
}

function update_from_github() {
    curl https://raw.githubusercontent.com/jacr13/tuto_docker_local_cluster/main/update_img.sh > $SCRIPT_PATH/update_img.sh
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
        -u|--update)
            UPDATE_SCRIPT=true
            shift
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
        -t|--tmp_folder)
            TMP_FOLDER_NAME="$2"
            shift 2
            ;;
        *)
            echo "Unknown error while processing options"
            exit 0
            ;;
    esac
done

IMG_PATH=$SCRIPT_PATH/"$IMG_NAME".sif

if [ "$UPDATE_SCRIPT" = true ]; then
    echo "Updating script..."
    update_from_github
fi

if [ "$CONNECTION" = true ]; then
    connect
fi

if [ -n "$DOCKER_REGISTRY" ]; then
    check_mv_old
    pull_image
else
    echo "If you are trying to pull an image don't forget to specify a docker registry."
fi


