import numpy as np

import torch
from torch import nn
import math

import torch.nn.functional as F

# official implementation
from torch.nn.utils import spectral_norm as sn_official
spectral_norm = sn_official


# much of this code taken from https://github.com/christiancosgrove/pytorch-spectral-normalization-gan


class Discriminator(nn.Module):
    def __init__(self, nn_type='dcgan',bn=True,skipinit=False, **kwargs):
        super().__init__()

        self.nn_type = nn_type
        self.max = 10
        self.bn = bn
        self.skipinit=skipinit
        if nn_type == 'dcgan':
            # adapted from pytorch website
            # https://pytorch.org/tutorials/beginner/dcgan_faces_tutorial.html#implementation

            # nc = number of input channels (input image size square)
            # ndf = number of filters, state sizes

            nc = 3
            ndf = 64
            leak = 0.2

            if bn:
                bn1 = nn.BatchNorm2d(ndf * 2)
                bn2 = nn.BatchNorm2d(ndf * 4)
                bn3 = nn.BatchNorm2d(ndf * 8)
            else:
                bn1 = nn.Identity()
                bn2 = nn.Identity()
                bn3 = nn.Identity()


            self.main = nn.Sequential(
                # input is (nc) x 64 x 64
                # nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding, dilation...)
                nn.Conv2d(nc, ndf, 4, 2, 1, bias=False),
                nn.LeakyReLU(leak, inplace=True),
                # state size. (ndf) x 32 x 32
                nn.Conv2d(ndf, ndf * 2, 4, 2, 1, bias=False),
                bn1,
                nn.LeakyReLU(leak, inplace=True),
                # state size. (ndf*2) x 16 x 16
                nn.Conv2d(ndf * 2, ndf * 4, 4, 2, 1, bias=False),
                bn2,
                nn.LeakyReLU(leak, inplace=True),
                # state size. (ndf*4) x 8 x 8
                nn.Conv2d(ndf * 4, ndf * 8, 4, 2, 1, bias=False),
                bn3,
                nn.LeakyReLU(leak, inplace=True),
                # state size. (ndf*8) x 4 x 4
                #nn.Conv2d(ndf * 8, 1, 4, 1, 0, bias=False),
                # change documented at https://github.com/pytorch/examples/issues/486
                nn.Conv2d(ndf * 8, 1, 2, 2, 0, bias=False),
                nn.Sigmoid()
            )

        elif nn_type == 'dcgan-ns':
            # dcgan, but without sigmoid for the last layer
            nc = 3
            ndf = 64
            leak = 0.2

            if bn:
                bn1 = nn.BatchNorm2d(ndf * 2)
                bn2 = nn.BatchNorm2d(ndf * 4)
                bn3 = nn.BatchNorm2d(ndf * 8)
            else:
                bn1 = nn.Identity()
                bn2 = nn.Identity()
                bn3 = nn.Identity()


            self.main = nn.Sequential(
                # input is (nc) x 64 x 64
                # nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding, dilation...)
                nn.Conv2d(nc, ndf, 4, 2, 1, bias=False),
                nn.LeakyReLU(leak, inplace=True),
                nn.Conv2d(ndf, ndf * 2, 4, 2, 1, bias=False),
                bn1,
                nn.LeakyReLU(leak, inplace=True),
                nn.Conv2d(ndf * 2, ndf * 4, 4, 2, 1, bias=False),
                bn2,
                nn.LeakyReLU(leak, inplace=True),
                nn.Conv2d(ndf * 4, ndf * 8, 4, 2, 1, bias=False),
                bn3,
                nn.LeakyReLU(leak, inplace=True),
                # state size. (ndf*8) x 4 x 4
                #nn.Conv2d(ndf * 8, 1, 4, 1, 0, bias=False),
                # change documented at https://github.com/pytorch/examples/issues/486
                nn.Conv2d(ndf * 8, 1, 2, 2, 0, bias=False)
            )

        elif nn_type == 'dcgan-sn':
            # adapted from https://github.com/christiancosgrove/pytorch-spectral-normalization-gan
            # dcgan with spectral norm from pytorch

            # defaults
            nc = 3
            ndf = 64
            leak = 0.1
            w_g = 4

            self.main = nn.Sequential(
                # layer 1
                spectral_norm(nn.Conv2d(nc, ndf, 3, 1, 1, bias=True)),
                nn.LeakyReLU(leak),
                # layer 2
                spectral_norm(nn.Conv2d(ndf, ndf, 4, 2, 1, bias=True)),
                nn.LeakyReLU(leak),
                #layer 3
                spectral_norm(nn.Conv2d(ndf, ndf * 2, 3, 1, 1, bias=True)),
                nn.LeakyReLU(leak),
                # layer 4
                spectral_norm(nn.Conv2d(ndf * 2, ndf * 2, 4, 2, 1, bias=True)),
                nn.LeakyReLU(leak),
                # layer 5
                spectral_norm(nn.Conv2d(ndf * 2, ndf * 4, 3, 1, 1, bias=True)),
                nn.LeakyReLU(leak),
                # layer 6
                spectral_norm(nn.Conv2d(ndf * 4, ndf * 4, 4, 2, 1, bias=True)),
                nn.LeakyReLU(leak),
                # layer 7
                spectral_norm(nn.Conv2d(ndf * 4, ndf * 8, 3, 1, 1, bias=True)),
                nn.LeakyReLU(leak),
                nn.Flatten(),
                spectral_norm(nn.Linear(w_g * w_g * 512, 1))
            )

        elif nn_type == 'resnet-sn':
            # adapted from https://github.com/christiancosgrove/pytorch-spectral-normalization-gan
            # with spectral norm from pytorch

            nc = 3
            self.disc_size = 128
            bn = self.bn
            skipinit=self.skipinit
            self.fc = nn.Linear(self.disc_size, 1)
            nn.init.xavier_uniform_(self.fc.weight.data, 1.)

            self.main = nn.Sequential(
                FirstResBlockDiscriminator(nc, self.disc_size, stride=2, sn=True,bn=bn,skipinit=skipinit),
                ResBlockDiscriminator(self.disc_size, self.disc_size, stride=2, sn=True,bn=bn,skipinit=skipinit),
                ResBlockDiscriminator(self.disc_size, self.disc_size, sn=True,bn=bn,skipinit=skipinit),
                ResBlockDiscriminator(self.disc_size, self.disc_size, sn=True,bn=bn,skipinit=skipinit),
                nn.ReLU(),
                nn.AvgPool2d(8),
                nn.Flatten(),
                spectral_norm(self.fc)
            )

        elif nn_type == 'resnet':
            # same as above, but without the spectral norm
            nc = 3
            self.disc_size = 128

            self.fc = nn.Linear(self.disc_size, 1)
            nn.init.xavier_uniform_(self.fc.weight.data, 1.)
            bn = self.bn
            self.main = nn.Sequential(
                FirstResBlockDiscriminator(nc, self.disc_size, stride=2, sn=False,bn=bn,skipinit=skipinit),
                ResBlockDiscriminator(self.disc_size, self.disc_size, stride=2, sn=False,bn=bn,skipinit=skipinit),
                ResBlockDiscriminator(self.disc_size, self.disc_size, sn=False,bn=bn,skipinit=skipinit),
                ResBlockDiscriminator(self.disc_size, self.disc_size, sn=False,bn=bn,skipinit=skipinit),
                nn.ReLU(),
                nn.AvgPool2d(8),
                nn.Flatten(),
                self.fc
            )

        else:
            raise NotImplementedError()
            


    def forward(self, input):
        output = self.main(input)
        output = nn.ReLU()(output+self.max)-self.max

        return output.view(-1, 1).squeeze(1)





### helpers, all from https://github.com/christiancosgrove/pytorch-spectral-normalization-gan


# for the spectral resnet

class ResBlockDiscriminator(nn.Module):

    def __init__(self, in_channels, out_channels, stride=1, sn=True,bn=True,skipinit=False):
        super(ResBlockDiscriminator, self).__init__()

        if sn:
            spec_norm = spectral_norm
        else:
            def spec_norm(x):
                return x
        if skipinit:
            self.bias = nn.Parameter(torch.tensor(0.))
            self.scaling = nn.Parameter(torch.tensor(0.))
        else:
            self.bias = 0.
            self.scaling =1.

        self.conv1 = nn.Conv2d(in_channels, out_channels, 3, 1, padding=1)
        self.conv2 = nn.Conv2d(out_channels, out_channels, 3, 1, padding=1)
        if bn:
            self.bn1 = nn.BatchNorm2d(out_channels)
            self.bn2 = nn.BatchNorm2d(out_channels)
        else:
            self.bn1 = nn.Identity()
            self.bn2 = nn.Identity()            
        nn.init.xavier_uniform_(self.conv1.weight.data, 1.)
        nn.init.xavier_uniform_(self.conv2.weight.data, 1.)

        if stride == 1:
            self.model = nn.Sequential(
                nn.ReLU(),
                spec_norm(self.conv1),
                self.bn1,
                nn.ReLU(),
                spec_norm(self.conv2),
                self.bn2
                )
        else:
            self.model = nn.Sequential(
                nn.ReLU(),
                spec_norm(self.conv1),
                self.bn1,
                nn.ReLU(),
                spec_norm(self.conv2),
                self.bn2,
                nn.AvgPool2d(2, stride=stride, padding=0)
                )
        self.bypass = nn.Sequential()
        if stride != 1:

            self.bypass_conv = nn.Conv2d(in_channels,out_channels, 1, 1, padding=0)
            nn.init.xavier_uniform_(self.bypass_conv.weight.data, np.sqrt(2))

            self.bypass = nn.Sequential(
                spec_norm(self.bypass_conv),
                nn.AvgPool2d(2, stride=stride, padding=0)
            )


    def forward(self, x):
        return self.scaling*self.model(x) + self.bypass(x) + self.bias

# special ResBlock just for the first layer of the discriminator
class FirstResBlockDiscriminator(nn.Module):

    def __init__(self, in_channels, out_channels, stride=1, sn=1,bn=True,skipinit=False):
        super(FirstResBlockDiscriminator, self).__init__()

        if sn == 1:
            spec_norm = spectral_norm
        else:
            def spec_norm(x):
                return x

        if skipinit:
            self.bias = nn.Parameter(torch.tensor(0.))
            self.scaling = nn.Parameter(torch.tensor(0.))
        else:
            self.bias = 0.
            self.scaling =1.
        self.conv1 = nn.Conv2d(in_channels, out_channels, 3, 1, padding=1)
        self.conv2 = nn.Conv2d(out_channels, out_channels, 3, 1, padding=1)
        self.bypass_conv = nn.Conv2d(in_channels, out_channels, 1, 1, padding=0)
        if bn:        
            self.bn1 = nn.BatchNorm2d(out_channels)
            self.bn2 = nn.BatchNorm2d(out_channels)
            self.bn3 = nn.BatchNorm2d(out_channels)
        else:
            self.bn1 = nn.Identity()
            self.bn2 = nn.Identity()
            self.bn3 = nn.Identity()
        nn.init.xavier_uniform_(self.conv1.weight.data, 1.)
        nn.init.xavier_uniform_(self.conv2.weight.data, 1.)
        nn.init.xavier_uniform_(self.bypass_conv.weight.data, np.sqrt(2))

        # we don't want to apply ReLU activation to raw image before convolution transformation.
        self.model = nn.Sequential(
            spec_norm(self.conv1),
            self.bn1,
            nn.ReLU(),
            spec_norm(self.conv2),
            self.bn2,
            nn.AvgPool2d(2)
            )
        self.bypass = nn.Sequential(
            nn.AvgPool2d(2),
            spec_norm(self.bypass_conv),
            self.bn3
        )

    def forward(self, x):
        return self.scaling*self.model(x) + self.bypass(x) + self.bias


