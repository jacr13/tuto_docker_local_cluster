import argparse
import os
import os.path as osp
import time

import numpy as np
import torch
import torch.nn as nn
import wandb
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, transforms


def get_dataloaders(batch_size):
    # Define transformations
    # 1. convert to tensor
    transform = transforms.Compose([transforms.ToTensor()])

    # Load MNIST dataset
    cifar_dataset = datasets.MNIST(
        root="./data", train=True, download=True, transform=transform
    )

    # Define the size of your validation set
    validation_set_size = int(
        0.1 * len(cifar_dataset)
    )  # 10% of the training set for validation

    # Split the dataset into training and validation sets
    train_set, validation_set = random_split(
        cifar_dataset, [len(cifar_dataset) - validation_set_size, validation_set_size]
    )

    # Create DataLoader for training, validation, and test sets
    train_loader = DataLoader(train_set, batch_size=batch_size, shuffle=True)
    validation_loader = DataLoader(validation_set, batch_size=batch_size, shuffle=False)

    # For the test set
    test_dataset = datasets.MNIST(
        root="./data", train=False, download=True, transform=transform
    )
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    return train_loader, validation_loader, test_loader


class MLP(nn.Module):
    def __init__(self, hidden_size):
        super(MLP, self).__init__()
        self.layers = nn.Sequential(
            nn.Linear(784, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, 10),
        )

    def forward(self, x):
        # convert tensor (128, 1, 28, 28) --> (128, 1*28*28)
        x = x.view(x.size(0), -1)
        x = self.layers(x)
        return x


def main(args):
    train_loader, validation_loader, test_loader = get_dataloaders(
        batch_size=args.batch_size
    )
    model = MLP(args.hidden_size).to(args.device)

    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    loss_fn = nn.CrossEntropyLoss()

    mean_train_losses = []
    mean_valid_losses = []
    valid_acc_list = []

    for epoch in range(args.epochs):
        model.train()

        train_losses = []
        valid_losses = []
        for i, (images, labels) in enumerate(train_loader):
            images = images.to(args.device)
            labels = labels.to(args.device)

            optimizer.zero_grad()

            outputs = model(images)
            loss = loss_fn(outputs, labels)
            loss.backward()
            optimizer.step()

            train_losses.append(loss.item())

        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for i, (images, labels) in enumerate(validation_loader):
                images = images.to(args.device)
                labels = labels.to(args.device)

                outputs = model(images)
                loss = loss_fn(outputs, labels)

                valid_losses.append(loss.item())

                _, predicted = torch.max(outputs.data, 1)
                correct += (predicted == labels).sum().item()
                total += labels.size(0)

        mean_train_losses.append(np.mean(train_losses))
        mean_valid_losses.append(np.mean(valid_losses))

        accuracy = 100 * correct / total
        valid_acc_list.append(accuracy)

        wandb.log(
            {
                "train_loss": np.mean(train_losses),
                "valid_loss": np.mean(valid_losses),
                "accuracy": accuracy,
            },
            step=epoch + 1,
        )

        print(
            "epoch : {}, train loss : {:.4f}, valid loss : {:.4f}, valid acc : {:.2f}%".format(
                epoch + 1, np.mean(train_losses), np.mean(valid_losses), accuracy
            )
        )

        # save model if best
        if np.mean(valid_losses) < np.min(mean_valid_losses):
            torch.save(
                model.state_dict(),
                osp.join(args.ckpt_dir, args.name, "best_model.pt"),
            )

        # save model every 10 epochs
        if (epoch + 1) % 10 == 0:
            torch.save(
                model.state_dict(),
                osp.join(args.ckpt_dir, args.name, f"epoch_{epoch + 1}.pt"),
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="simple experiment to test wandb",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # wandb
    parser.add_argument("--wandb_project", help="wandb project name", default="DEFAULT")
    parser.add_argument("--wandb_entity", help="wandb entity name", default=None)
    parser.add_argument("--wandb_mode", help="wandb mode", default="online")
    parser.add_argument(
        "--wandb_run_path",
        help='wandb run path in the form "<entity>/<project>/<run_id>"',
        default=None,
    )
    parser.add_argument(
        "--wandb_download_replace",
        action="store_true",
        default=False,
    )

    # experiment
    parser.add_argument(
        "--name", help="experiment_name", default=f"test_wandb_{int(time.time())}"
    )
    parser.add_argument("--log_dir", help="experiment_name", default="logs")
    parser.add_argument("--ckpt_dir", help="experiment_name", default="checkpoints")

    parser.add_argument("--epochs", help="number of epochs", default=10)
    parser.add_argument("--batch_size", help="batch size", default=128)
    parser.add_argument("--hidden_size", help="hidden layer size", default=100)
    parser.add_argument("--device", help="device", default="cuda")

    args = parser.parse_args()

    if args.device.startswith("cuda") and not torch.cuda.is_available():
        print("No GPU available, using CPU instead")
        args.device = "cpu"

    print("Using device : ", args.device)

    experiment_name = args.name
    group = "test_wandb"

    log_dir = osp.join(args.log_dir, experiment_name)
    os.makedirs(log_dir, exist_ok=True)

    ckpt_dir = osp.join(args.ckpt_dir, experiment_name)
    os.makedirs(ckpt_dir, exist_ok=True)

    wandb.init(
        project=args.wandb_project,
        name=experiment_name,
        id=experiment_name,
        group=group,
        config=vars(args),
        dir=log_dir,
        entity=args.wandb_entity,
        mode=args.wandb_mode,
    )

    main(args)
