#!/bin/bash


#creates a local volume and adds them in 

create_local_volume () {
    volume_name=$1
    volume_path=$2
    volume_mount_path=$3
    size=$4
    count=$5

    dev_path=${2}/${1}

    sudo dd if=/dev/zero of=${dev_path} bs=${size} count=${count}

    sudo mkfs.ext4 ${dev_path}
    DISK_UUID=$(sudo blkid -s UUID -o value ${dev_path})

    disk_mount_path=${volume_mount_path}/${DISK_UUID}

    sudo mkdir -p $disk_mount_path
    sudo mount -t ext4 ${dev_path} ${disk_mount_path}
    echo ${dev_path} ${disk_mount_path} ext4 defaults 0 2 | sudo tee -a /etc/fstab

    echo "created ext4 volume image at ${dev_path} and mounted at ${disk_mount_path} with uuid ${DISK_UUID}"
}

VOLUME_NAME=$1
VOLUME_PATH=$2
VOLUME_MOUNT_PATH=$3
SIZE=$4
COUNT=$5

create_local_volume $VOLUME_NAME $VOLUME_PATH $VOLUME_MOUNT_PATH $SIZE $COUNT