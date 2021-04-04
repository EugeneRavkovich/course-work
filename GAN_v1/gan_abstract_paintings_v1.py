# -*- coding: utf-8 -*-
"""GAN_abstract_paintings_v1.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1LLbUC_joHokXAJVs6CEBPZjIzIKP3suX
"""

!pip install opendatasets --upgrade --quiet

import opendatasets as od
import torch
import torch.nn as nn
import torch.optim as optim
import os
from torchvision.datasets import ImageFolder
import torchvision.transforms as tt
from torch.utils.data import DataLoader
from torchvision.utils import make_grid
import matplotlib.pyplot as plt
from torchvision.utils import save_image
from tqdm.notebook import tqdm

dataset_url = 'https://www.kaggle.com/greg115/abstract-art'
od.download(dataset_url)

data_dir = './abstract-art'
print(os.listdir(data_dir))

print(os.listdir(data_dir+'/abstract_art_512')[:10])

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
img_size = 128
num_channels = 3
latent_size = 100
batch_size = 128
features_g = 64
features_d = 16
num_epochs = 300
lr = 2e-4
fixed_latent = torch.randn(batch_size, latent_size, 1, 1).to(device)
criterion = nn.BCELoss().to(device)

train_ds = ImageFolder(root=data_dir,
                      transform=tt.Compose([
                        tt.Resize(img_size),
                        tt.ToTensor(),
                        tt.Normalize((0.5), (0.5))
                      ]))

train_dl = DataLoader(train_ds, batch_size, shuffle=True, num_workers=2, drop_last=True)

def show_batch(dl):
  for images, _ in dl:
    fig, ax = plt.subplots(figsize=(8,8))
    ax.set_xticks([]); ax.set_yticks([])
    ax.imshow(make_grid(images[:64], normalize=True).permute(1, 2, 0))
    break

show_batch(train_dl)

class Generator(nn.Module):
  def __init__(self, features_g, latent_size, num_channels):
    super(Generator, self).__init__()
    self.net = nn.Sequential(
        self.deConvBlock(latent_size, features_g*16, 4, 1, 0),
        self.deConvBlock(features_g*16, features_g*8, 4, 2, 1),
        self.deConvBlock(features_g*8, features_g*4, 4, 2, 1),
        self.deConvBlock(features_g*4, features_g*2, 4, 2, 1),
        self.deConvBlock(features_g*2, features_g, 4, 2, 1),
        nn.ConvTranspose2d(features_g, num_channels, 4, 2, 1),
        nn.Tanh()
    )

  def deConvBlock(self, in_channels, out_channels, kernel_size, stride, padding, bias=False):
    return nn.Sequential(
        nn.ConvTranspose2d(in_channels, out_channels, kernel_size, stride, padding, bias=bias),
        nn.BatchNorm2d(out_channels),
        nn.LeakyReLU(0.2, inplace=True),
        #nn.ReLU(inplace=True),
    )

  def forward(self, x):
    return self.net(x)

class Discriminator1(nn.Module):
  def __init__(self, features_d, num_channels):
    super(Discriminator1, self).__init__()
    self.net = nn.Sequential(
        nn.Conv2d(num_channels, features_d, 4, 2, 1, bias=False),
        nn.LeakyReLU(0.2, inplace=True),
        self.ConvBlock(features_d, features_d*2, 4, 2, 1, bias=False),
        self.ConvBlock(features_d*2, features_d*4, 4, 2, 1, bias=False),
        self.ConvBlock(features_d*4, features_d*8, 4, 2, 1, bias=False),
        self.ConvBlock(features_d*8, features_d*16, 4, 2, 1, bias=False),
        nn.Conv2d(features_d*16, 1, 4, 1, 0, False),
        nn.Flatten(),
        nn.Sigmoid()
    )


  def ConvBlock(self, in_channels, out_channels, kernel_size, stride, padding, bias=False):
    return nn.Sequential(
        nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding, bias=bias),
        nn.BatchNorm2d(out_channels),
        nn.LeakyReLU(0.2, inplace=True),
    )

  def forward(self, x):
    return self.net(x)

class Discriminator(nn.Module):
    def __init__(self, features_d, num_channels):
        super(Discriminator, self).__init__()
        self.main = nn.Sequential(
            nn.Conv2d(num_channels, features_d, 4, stride=2, padding=1, bias=False), 
            nn.BatchNorm2d(features_d),
            nn.LeakyReLU(0.2, inplace=True),
            # state size. (ndf) x 64 x 64
            nn.Conv2d(features_d, features_d* 2, 4, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(features_d * 2),
            nn.LeakyReLU(0.2, inplace=True),
            # state size. (ndf*2) x 32 x 32
            nn.Conv2d(features_d * 2, features_d * 4, 4, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(features_d * 4),
            nn.LeakyReLU(0.2, inplace=True),
            # state size. (ndf*4) x 16 x 16 
            nn.Conv2d(features_d * 4, features_d * 8, 4, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(features_d * 8),
            nn.LeakyReLU(0.2, inplace=True),
            # state size. (ndf*8) x 8 x 8
            nn.Conv2d(features_d * 8, features_d * 16, 4, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(features_d * 16),
            nn.LeakyReLU(0.2, inplace=True),
            # state size. (ndf*16) x 4 x 4
            nn.Conv2d(features_d * 16, 1, 4, stride=1, padding=0, bias=False),
            nn.Flatten(),
            nn.Sigmoid()
            # state size. 1
        )

    def forward(self, input):
        return self.main(input)

def initialize_weights(model):
  for module in model.modules():
    if isinstance(module, (nn.Conv2d, nn.ConvTranspose2d)):
      nn.init.normal_(module.weight.data, 0.0, 0.02)
    elif isinstance(module, nn.BatchNorm2d):
      nn.init.normal_(module.weight.data, 1.0, 0.02)
      nn.init.constant_(module.bias.data, 0)

netG = Generator(features_g, latent_size, num_channels).to(device)
netD = Discriminator(features_d, num_channels).to(device)
initialize_weights(netG)
initialize_weights(netD)

optimG = optim.Adam(netG.parameters(), lr=lr, betas=(0.5, 0.999))
optimD = optim.Adam(netD.parameters(), lr=lr, betas=(0.5, 0.999))

sample_dir = 'generated'
os.makedirs(sample_dir, exist_ok=True)

def save_samples(index, latent, show=True):
  fake_images = netG(latent)[:25]
  fake_fname = 'generated-images-{0:0=4d}.png'.format(index)
  grid = make_grid(fake_images.cpu().detach(), nrow=5, normalize=True)
  save_image(grid, os.path.join(sample_dir, fake_fname))
  if show:
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.set_xticks([]); ax.set_yticks([])
    ax.imshow(grid.permute(1, 2, 0))

save_samples(0, fixed_latent)

real_targets = (torch.ones(batch_size, 1) - torch.rand(batch_size, 1) * 0.2).to(device)
fake_targets = (torch.zeros(batch_size, 1) + torch.rand(batch_size, 1) * 0.2).to(device)
losses_g, losses_d = [], [] 
for epoch in range(num_epochs):
  for batch_idx, (images, _) in enumerate(tqdm(train_dl)):
    # training discriminator
    netD.zero_grad()
    images = images.to(device)
    real_preds = netD(images)
    disc_real_loss = criterion(real_preds, real_targets)
    real_score = torch.mean(real_preds).item()
    noise = torch.randn(batch_size, latent_size, 1, 1).to(device)
    fake_images = netG(noise)
    fake_preds = netD(fake_images.detach())
    disc_fake_loss = criterion(fake_preds, fake_targets)
    fake_score = torch.mean(fake_preds).item()
    disc_loss = torch.log(disc_real_loss) + torch.log(disc_fake_loss)
    disc_loss.backward()
    optimD.step()

    # training generator
    netG.zero_grad()
    
    upd_fake_preds = netD(fake_images)
    gen_loss = torch.log(criterion(upd_fake_preds, real_targets))
    upd_fake_score = torch.mean(upd_fake_preds).item()
    """
    fake = netG(noise)
    preds = netD(fake)
    gen_loss = criterion(preds, real_targets)
    upd_fake_score = torch.mean(preds).item()
    """
    y = gen_loss
    gen_loss.backward()
    optimG.step()

    losses_d.append(disc_loss)
    losses_g.append(gen_loss)

  print('Epoch [{}/{}], Loss_D: {:.4f}, Loss_G: {:.4f}, D(x): {:.4f}, D(G(z)): {:.4f}/{:.4f}'.format(
      epoch+1, num_epochs, disc_loss, gen_loss, real_score, fake_score, upd_fake_score
  ))
  with torch.no_grad():
    save_samples(epoch+1, fixed_latent, show=False)

import cv2
import os

image_folder = 'generated'
video_name = 'video3.avi'

images = [img for img in os.listdir(image_folder) if img.endswith(".png")]
frame = cv2.imread(os.path.join(image_folder, images[0]))
height, width, layers = frame.shape

video = cv2.VideoWriter(video_name, 0, 4, (width,height))

for image in images:
    video.write(cv2.imread(os.path.join(image_folder, image)))

cv2.destroyAllWindows()
video.release()

for epoch in range(num_epochs):
  for batch_idx, (images, _) in enumerate(tqdm(train_dl)):
    # training discriminator
    netD.zero_grad()
    images = images.to(device)
    real_preds = netD(images)
    disc_real_loss = criterion(real_preds, real_targets)
    real_score = torch.mean(real_preds).item()
    noise = torch.randn(batch_size, latent_size, 1, 1).to(device)
    fake_images = netG(noise)
    fake_preds = netD(fake_images.detach())
    disc_fake_loss = criterion(fake_preds, fake_targets)
    fake_score = torch.mean(fake_preds).item()
    disc_loss = torch.log(disc_real_loss) + torch.log(disc_fake_loss)
    disc_loss.backward()
    optimD.step()

    # training generator
    netG.zero_grad()
    
    upd_fake_preds = netD(fake_images)
    gen_loss = torch.log(criterion(upd_fake_preds, real_targets))
    upd_fake_score = torch.mean(upd_fake_preds).item()
    """
    fake = netG(noise)
    preds = netD(fake)
    gen_loss = criterion(preds, real_targets)
    upd_fake_score = torch.mean(preds).item()
    """
    y = gen_loss
    gen_loss.backward()
    optimG.step()

    losses_d.append(disc_loss)
    losses_g.append(gen_loss)

  print('Epoch [{}/{}], Loss_D: {:.4f}, Loss_G: {:.4f}, D(x): {:.4f}, D(G(z)): {:.4f}/{:.4f}'.format(
      epoch+1, num_epochs, disc_loss, gen_loss, real_score, fake_score, upd_fake_score
  ))
  with torch.no_grad():
    save_samples(epoch+301, fixed_latent, show=False)

