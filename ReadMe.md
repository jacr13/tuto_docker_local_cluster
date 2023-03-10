# Tutorial on docker and docker on cluster

## Docker
To create a docker image you need to create a `Dockerfile` and add to it all the necessary packages you need to run your project.
I have included an example file taken from [here](https://hub.docker.com/repository/docker/dmml/conda/general).

First let us pull a conda image from docker hub.

```bash
docker pull dmml/conda:py39
```

you can already use this image, if you want to run a hello world example:

```bash
docker run --rm dmml/conda:py39 python -c "print('hello world')"
```

if you want to get inside the image use the `-it` parameter
```bash
docker run --rm  -it dmml/conda:py39 bash
```

to quit the container type `exit`.

Now let's imagine that you have a much more complex project, with a number of python packages to install, and you want to create a docker image for this specific project. You can base the new image on the conda image you already have using the `Dockerfile` file provided.
You can build the image using the same command as before:
```bash
docker build -t <username/image_name:tag> -f Dockerfile .
```

Now we can test our new image by running our project_example insider docker.

```bash
docker run -v $(pwd)/project_example:/workspace <username/image_name:tag> python main.py
```

The -v parameter allows you to mount folders insider your container.

If everything went correctly until now, you can push the image to docker hub to access it from the cluster later.
```bash
docker push <username/image_name:tag>
```

If you want to use the docker hub account of the group, replace username by dmml and follow instructions [here](https://bitbucket.org/dmmlgeneva/dockerhub/src/master/).

## Cluster

Connect to the cluster:

```bash
# LOCAL
# connect to yggdrasil
ssh <your_username>@login1.yggdrasil.hpc.unige.ch

# connect to baobab
ssh <your_username>@login2.baobab.hpc.unige.ch 
```

Create a folder on your home directory where you will store your docker images.

```bash
# CLUSTER
mkdir $HOME/docker
```

Copy update_img.sh script to the docker folder on the cluster (use this command on your local machine)

```bash
# LOCAL
# if you use yggdrasil
rsync -rvaP update_img.sh <your_cluster_username>@login1.yggdrasil.hpc.unige.ch:~/docker/.

# if you use baobab
rsync -rvaP update_img.sh <your_cluster_username>@login2.baobab.hpc.unige.ch:~/docker/.
```

Now you are ready to import your docker images on the cluster using singularity.
Since we use singularity, we need to load it, you can do it manually each time you use singularity or you can load it by default by adding it to your .bashrc file:

```bash
# CLUSTER
# load manually
module load GCCcore/8.2.0 Singularity/3.4.0-Go-1.12

# set it to your .bashrc file
echo "module load GCCcore/8.2.0 Singularity/3.4.0-Go-1.12" > $HOME/.bashrc
source $HOME/.bashrc
```

Now that you have loaded singularity we can use the script to import your images from docker hub:

```bash
# CLUSTER
# go the docker folder on the cluster
cd $HOME/docker
# you can check how the script works
./update_img.sh -h
# OUTPUT:
# usage:  [-vhc] [-du docker_username] [-dp docker_password] [-dr docker_registry] [-n name] [-o old_folder]
#   -v                      version
#   -h                      display help
#   -c                      connect to docker
#   -du docker_username     specify the docker username (neeeds c parameter to connect to docker)
#   -dp docker_password     specify the docker password (neeeds c parameter to connect to docker)
#   -dr docker_registry     specify the docker registry, eg. candidj0/milozero:latest
#   -n  name                specify the name of the image (to be saved), eg. milozero
#   -o  old_folder          specify the name of the folder where to save old images
```

Some comments: the `-c` argument is only needed if your image is in a private docker registry, if this is the case you need to provide the username and password of your docker hub account and add the following parameters to the command:

```bash
./update_img.sh -c -du <docker_username> -dp <docker_password> -dr <docker_registry> -n <image_name>

# e.g. if you use a private repository in dmml docker hub, you should specify
./update_img.sh -c -du dmml -dp password -dr <docker_registry> -n <image_name> 
```

otherwise, you can simply run the script with following parameters:

```bash
./update_img.sh -dr <docker_registry> -n <image_name>
```

<docker_registry> should be replaced with the docker registry, something like: username/image:tag (the username here is the dockerhub username)
and <image_name> should be replaced with the name of the image that will be saved on the cluster, eg. my_docker_img.

After this you can run your code inside the image!

### How to run code on the cluster

create a file to specify your experiment, lets say you create a file named <exp_filename>.sh and you put this inside (pay attention <placeholders> should be replaced)

```bash
#!/usr/bin/env bash

#SBATCH --job-name=<name_your_experiment>
#SBATCH --partition=<should be a partition, or a comma separeted list of partitions>
#SBATCH --ntasks=1
#SBATCH --gres=gpu:1            # only if you use gpu otherwise remove this line
#SBATCH --time=4-00:00:00
#SBATCH --mem=<The ram that you need, eg. for 32G you can specify 32000>
#SBATCH --output=./out/run_%j.out
#SBATCH --error=./out/run_e%j.out

# load here the modules you need, for example:
module load GCC/10.2.0 CUDA/11.1.1 GCCcore/8.2.0 Singularity/3.4.0-Go-1.12

# specify the command to run
srun singularity run -B $HOME/scratch:/scratch $HOME/docker/<image_name>.sif \
 bash -c "export WANDB_BASE_URL='https://api.wandb.ai'; \
 export WANDB_API_KEY='<your_key>'; \
 cd $HOME/path/to/your/code; \
 python main.py \
 --arg_1=my_first_arg \
 --arg_2=my_second_arg \
 --my_bool_arg 
```

Then, finally launch your experiment:

```bash
sbatch <exp_filename.sh>
```

Some useful commands:

1. view the queue
```bash
# verify the queue (see your experiments status, etc.)
squeue -u <your_username>
# or more general command
squeue -u $(whoami)
#or
squeue -u $USER
```

2.  cancel your jobs
```bash
# cancel all your jobs
scancel -u <your_username>
# or more general command
scancel -u $(whoami)
# or
scancel -u $USER

# cancel a specific job
scancel <job_id>

```

3. Advanced commands

I provided my own custom commands for the cluster, the most useful command is:
```bash
my_scancel -h
# OUTPUT:
# Usage: my_scancel_invert [option...]
#    -h, --help             Show this help message
#    -p, --pattern [text]   pattern to match on grep (will cancel all jobs that match this pattern)
#    -i, --invert           invert the pattern, so now this command will KEEP jobs that match the pattern
#    -nd, --no_dryrun       Doesn't show jobs in dry run mode (dangerous)
# 
# This command will cancel all the jobs of USER that match pattern if neither -i or --invert are specified, and cancel all jobs that DO NOT match the pattern if -i or --invert are specified!
```

- `my_scancel` : cancel all my jobs

- `my_scancel -p <pattern>`: this command will cancel all jobs that match the pattern

- `my_scancel -i -p <pattern>` : this command will cancel all jobs that DO NOT match the pattern
  
But you have also:

- `my_squeue` : shortcut to `squeue -u $USER`
  
- Changes the PS1 to show git branch, e.g.
  
    `(yggdrasil)-username@login1:~/path/to/git/folder $`

    becomes

    `(yggdrasil)-username@login1:~/path/to/git/folder (branch)$`

To use this commands you need to add this file to the cluster and add it to your .bashrc file:
```bash
# copy the file to the cluster
# LOCAL
# if you use yggdrasil
rsync -rvaP my_cluster_cmds.sh <your_username>@login1.yggdrasil.hpc.unige.ch:.

# if you use baobab
rsync -rvaP my_cluster_cmds.sh <your_username>@login2.baobab.hpc.unige.ch:.
```
and add it to your .bashrc on the cluster:

```bash
# Add the file to your .bashrc
# CLUSTER
echo "source $HOME/my_cluster_cmds.sh" > $HOME/.bashrc
source $HOME/.bashrc
```
