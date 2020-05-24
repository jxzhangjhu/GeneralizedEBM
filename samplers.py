import torch
import numpy as np
import time
import math
from torch.autograd import Variable
from torch.autograd.variable import Variable
from torch import nn

import torch.nn.functional as F
 
class Latent_potential(nn.Module):

    def __init__(self, generator,discriminator,latent_prior, temperature=100):
        #super(Latent_potential).__init__()
        super().__init__()
        self.generator = generator
        self.discriminator = discriminator
        self.latent_prior = latent_prior
        self.temperature = temperature
    def forward(self,Z):
        #with torch.no_grad():
        out = self.generator(Z)
        out =  self.discriminator(out)
        out = -self.latent_prior.log_prob(Z) + self.temperature*out 
        #out = 0.5 * torch.norm(Z, dim=1) ** 2 + out
        #out = 0.5 * torch.norm(Z, dim=1) ** 2 + out

        return out

class Independent_Latent_potential(nn.Module):

    def __init__(self, generator,discriminator,latent_prior):
        #super(Latent_potential).__init__()
        super().__init__()
        self.generator = generator
        self.discriminator = discriminator
        self.latent_prior = latent_prior
    def forward(self,Z):
        #with torch.no_grad():
        out = self.generator(Z)
        out =  self.discriminator(out)
        return out 

class Dot_Latent_potential(nn.Module):

    def __init__(self, generator,discriminator,latent_prior):
        #super(Latent_potential).__init__()
        super().__init__()
        self.generator = generator
        self.discriminator = discriminator
        self.latent_prior = latent_prior
    def forward(self,Z):
        #with torch.no_grad():
        out = self.generator(Z)
        out =  self.discriminator(out)
        return  torch.norm(Z, dim=1) + out 

class Grad_potential(nn.Module):
    def __init__(self, potential):
        super().__init__()
        self.potential = potential
    def forward(self,X):
        X.requires_grad_()
        out = self.potential(X).sum()
        out.backward()
        return X.grad

class Grad_cond_potential(nn.Module):
    def __init__(self, potential):
        super().__init__()
        self.potential = potential
    def forward(self,X, labels):
        X.requires_grad_()
        Z = X,labels
        out = self.potential(Z).sum()
        out.backward()
        return X.grad


class LMCsampler(object):
    def __init__(self, potential, momentum,  T=100, num_steps_min=10, num_steps_max=20, gamma=1e-2,kappa = 4e-2):          
        
        self.momentum = momentum
        self.potential = potential
        
        self.num_steps_min = num_steps_min
        self.num_steps_max = num_steps_max
        self.kappa = kappa
        self.gamma = gamma


        self.grad_potential = Grad_potential(self.potential)
        self.T = T
        self.dUdX = None
        #self.grad_momentum = Grad_potential(self.momentum.log_prob)
        #self.sampler_momentum = momentum_sampler 
        
    def sample(self,prior_z,sample_chain=False,T=None,thinning=10):
        if T is None:
            T = self.T
        sampler = torch.distributions.Normal(torch.zeros_like(prior_z), 1.)
        
        #self.momentum.eval()
        self.potential.eval()
        t_extract_list = []
        Z_extract_list = []
        avg_acceptence_list  = []

        #num_steps = np.random.randint(self.num_steps_min, self.num_steps_max + 1)
        num_steps =1
        U  =  torch.zeros([prior_z.shape[0]]).to(prior_z.device)

        Z_t = prior_z.clone().detach()
        V_t = torch.zeros_like(Z_t)
        #V_t = self.momentum.sample([Z_t.shape[0]])
        t_extract_list.append(0)
        Z_extract_list.append(Z_t)
        avg_acceptence_list.append(1.)

        Z_0 = prior_z.clone().detach()
        V_0 = torch.zeros_like(Z_t)
        gamma = self.gamma
        for t in range(1, T+1):
            # reset computation graph
            #V_t = self.momentum.sample([Z_t.shape[0]])
            #U = U.uniform_(0,1)
            #Z_new,V_new = self.leapfrog(Z_t,V_t,self.grad_potential,sampler,T=num_steps,gamma=self.gamma,kappa=self.kappa)
            #V_t = torch.zeros_like(Z_t)
            #Z_t,V_t = self.leapfrog(Z_t,V_t,self.grad_potential,sampler,T=num_steps,gamma=self.gamma,kappa=self.kappa)
            Z_t,V_t = self.leapfrog(Z_t,V_t,self.grad_potential,sampler,T=num_steps,gamma=gamma,kappa=self.kappa)
            if t>0 and t%200==0:
                gamma *=0.1
                print('decreasing lr for sampling')            
            #Z_tmp,V_tmp,acc_prob = self.hasing_metropolis(Z_new, V_new, Z_t, V_t, self.potential,self.momentum.log_prob, U)
            #Z_t,V_t,acc_prob = self.hasing_metropolis_2(Z_new, V_new, Z_t,V_t, Z_0, V_0, self.potential,self.momentum.log_prob, U)
            #Z_t = Z_new
            #V_t = V_new
            #Z_t,acc_prob = self.hasing_metropolis(Z_new, V_new, Z_t, V_t, self.potential,self.momentum.log_prob, U)
            #print( 'avg_acceptence: ' +  str(acc_prob.mean().item() ) + ', iteration: '+ str(t))
            # only if extracting the samples so we have a sequence of samples
            if sample_chain and thinning != 0 and t % thinning == 0:
                t_extract_list.append(t)
                Z_extract_list.append(Z_t.clone().detach().cpu())
                #avg_acceptence_list.append(acc_prob.mean().item())
                avg_acceptence_list.append(1.)
            #print('iteration: '+ str(t))
        if not sample_chain:
            return Z_t.clone().detach(), 1.
        return t_extract_list, Z_extract_list,avg_acceptence_list
    # def sample(self,prior_z,sample_chain=False,T=None,thinning=10):
    #     if T is None:
    #         T = self.T
    #     sampler = torch.distributions.Normal(torch.zeros_like(prior_z), 1.)
        
    #     #self.momentum.eval()
    #     self.potential.eval()
    #     t_extract_list = []
    #     Z_extract_list = []
    #     accept_proba_list = []


    #     num_steps = np.random.randint(self.num_steps_min, self.num_steps_max + 1)
    #     num_steps = 1
    #     U  =  torch.zeros([prior_z.shape[0]]).to(prior_z.device)

    #     Z_t = prior_z.clone().detach()
    #     t_extract_list.append(0)
    #     Z_extract_list.append(Z_t)
        
    #     for t in range(T):
    #         # reset computation graph
    #         V_t = self.momentum.sample([Z_t.shape[0]])
    #         U = U.uniform_(0,1)
    #         #Z_new,V_new = self.leapfrog(Z_t,V_t,self.grad_potential,sampler,T=num_steps,gamma=self.gamma,kappa=self.kappa)
    #         Z_new,V_new = self.leapfrog(Z_t,V_t,self.grad_potential,sampler,T=num_steps,gamma=self.gamma,kappa=self.kappa)
    #         V_new = -V_new
    #         Z_t,V_t,acc_prob = self.hasing_metropolis(Z_new, V_new, Z_t, V_t, self.potential,self.momentum.log_prob, U)
    #         # only if extracting the samples so we have a sequence of samples
    #         if sample_chain and thinning != 0 and t % thinning == 0:
    #             t_extract_list.append(t)
    #             Z_extract_list.append(Z_t.clone().detach().cpu())
    #             accept_proba_list.append(acc_prob.clone().detach().cpu())
    #         #print('iteration: '+ str(t))
    #     if not sample_chain:
    #         return Z_t.clone().detach()
    #     return t_extract_list, Z_extract_list


    def leapfrog(self,x,v,grad_x,sampler,T=100,gamma=1e-2,kappa=4e-2):
        x_t = x.clone().detach()
        v_t = v.clone().detach()

        C = np.exp(-kappa * gamma)
        D = np.sqrt(1 - np.exp(-2 * kappa * gamma))
        for t in range(T):
            # reset computation graph
            x_t.detach_()
            v_t.detach_()
            x_half = x_t + gamma / 2 * v_t
            # calculate potentials and derivatives
            dUdX = grad_x(x_half)
            # update values
            v_half = v_t - gamma / 2 * dUdX
            v_tilde = C * v_half + D * sampler.sample()
            #v_tilde  = v_half
            v_t = v_tilde - gamma / 2 * dUdX
            x_t = x_half + gamma / 2 * v_t

        return x_t, v_t

    # def leapfrog(self,x,v,grad_x,sampler,T=100,gamma=1e-2,kappa=4e-2):
    #     x_t = x.clone().detach()
    #     v_t = v.clone().detach()
    #     for t in range(T):
    #         # reset computation graph
    #         x_t.detach_()
    #         v_t.detach_()
            
    #         if self.dUdX is None:
    #             x_tmp = 1.*x_t
    #             self.dUdX = grad_x(x_tmp).clone()
    #         # update values
    #         v_half = v_t - gamma / 2 * self.dUdX
    #         v_half.detach_()
    #         x_out = x_t +   gamma *v_half
    #         self.dUdX = 1.*grad_x(x_out).clone()
    #         x_t = x_out.clone()
    #         v_t    = v_half - gamma / 2 * self.dUdX
    #     return x_t, v_t


    def hasing_metropolis(self,Z_new, V_new, Z_0, V_0, potential, momentum,U):
        momentum_0 = -momentum(V_0)
        potential_0 = potential(Z_0)
        potential_new = potential(Z_new)
        momentum_new = -momentum(V_new)

        H0 = potential_0 + momentum_0
        H  = potential_new + momentum_new 

        difference = -H + H0
        acc_prob = torch.exp(-F.relu(-difference))
        accepted = U < acc_prob
        Z_out = 1.*Z_0
        V_out = 1.*V_0
        Z_out[accepted] = 1.* Z_new[accepted]
        V_out[accepted] = 1.*V_new[accepted]
        return Z_out, V_out, acc_prob

    def hasing_metropolis_2(self,Z_new, V_new, Z_t,V_t, Z_0, V_0, potential, momentum,U):
        momentum_0 = -momentum(V_0)
        potential_0 = potential(Z_0)
        potential_new = potential(Z_new)
        momentum_new = -momentum(V_new)

        H0 = potential_0 + momentum_0
        H  = potential_new + momentum_new 

        difference = -H + H0
        acc_prob = torch.exp(-F.relu(-difference))
        accepted = U < acc_prob
        Z_out = 1.*Z_t
        V_out = 1.*V_t
        Z_out[accepted] = 1.* Z_new[accepted]
        V_out[accepted] = 1.*V_new[accepted]
        return Z_out, V_out, acc_prob

class HMCsampler(object):
    def __init__(self, potential, momentum,  T=100, num_steps_min=10, num_steps_max=20, gamma=1e-2,kappa = 4e-2):          
        
        self.momentum = momentum
        self.potential = potential
        
        self.num_steps_min = num_steps_min
        self.num_steps_max = num_steps_max
        self.kappa = kappa
        self.gamma = gamma


        self.grad_potential = Grad_potential(self.potential)
        self.T = T
        self.dUdX = None

    def sample(self,prior_z,sample_chain=False,T=None,thinning=10):
        if T is None:
            T = self.T
        sampler = torch.distributions.Normal(torch.zeros_like(prior_z), 1.)
        
        #self.momentum.eval()
        self.potential.eval()
        t_extract_list = []
        Z_extract_list = []
        accept_proba_list = []


        num_steps = np.random.randint(self.num_steps_min, self.num_steps_max + 1)
        num_steps = 1
        U  =  torch.zeros([prior_z.shape[0]]).to(prior_z.device)

        Z_t = prior_z.clone().detach()
        t_extract_list.append(0)
        Z_extract_list.append(Z_t)
        
        for t in range(T):
            # reset computation graph
            V_t = self.momentum.sample([Z_t.shape[0]])
            U = U.uniform_(0,1)
            Z_new,V_new = self.leapfrog(Z_t,V_t,self.grad_potential,sampler,T=num_steps,gamma=self.gamma,kappa=self.kappa)
            V_new = -V_new
            Z_t,V_t,acc_prob = self.hasing_metropolis(Z_new, V_new, Z_t, V_t, self.potential,self.momentum.log_prob, U)
            # only if extracting the samples so we have a sequence of samples
            if sample_chain and thinning != 0 and t % thinning == 0:
                t_extract_list.append(t)
                Z_extract_list.append(Z_t.clone().detach().cpu())
                accept_proba_list.append(acc_prob.clone().detach().cpu())
        if not sample_chain:
            return Z_t.clone().detach()
        return t_extract_list, Z_extract_list

    def leapfrog(self,x,v,grad_x,sampler,T=100,gamma=1e-2,kappa=4e-2):
        x_t = x.clone().detach()
        v_t = v.clone().detach()
        for t in range(T):
            # reset computation graph
            x_t.detach_()
            v_t.detach_()
            
            if self.dUdX is None:
                x_tmp = 1.*x_t
                self.dUdX = grad_x(x_tmp).clone()
            # update values
            v_half = v_t - gamma / 2 * self.dUdX
            v_half.detach_()
            x_out = x_t +   gamma *v_half
            self.dUdX = 1.*grad_x(x_out).clone()
            x_t = x_out.clone()
            v_t    = v_half - gamma / 2 * self.dUdX
        return x_t, v_t


    def hasing_metropolis(self,Z_new, V_new, Z_0, V_0, potential, momentum,U):
        momentum_0 = -momentum(V_0)
        potential_0 = potential(Z_0)
        potential_new = potential(Z_new)
        momentum_new = -momentum(V_new)

        H0 = potential_0 + momentum_0
        H  = potential_new + momentum_new 

        difference = -H + H0
        acc_prob = torch.exp(-F.relu(-difference))
        accepted = U < acc_prob
        Z_out = 1.*Z_0
        V_out = 1.*V_0
        Z_out[accepted] = 1.* Z_new[accepted]
        V_out[accepted] = 1.*V_new[accepted]
        return Z_out, V_out, acc_prob


class LangevinSampler(object):
    def __init__(self, potential, T=100,  gamma=1e-2):          
        
        self.potential = potential
        
        #self.num_steps_min = num_steps_min
        #self.num_steps_max = num_steps_max
        self.gamma = gamma
        self.grad_potential = Grad_potential(self.potential)
        self.T = T
        #self.grad_momentum = Grad_potential(self.momentum.log_prob)
        #self.sampler_momentum = momentum_sampler 
        
    def sample(self,prior_z,sample_chain=False,T=None,thinning=10):
        if T is None:
            T = self.T
        sampler = torch.distributions.Normal(torch.zeros_like(prior_z), 1.)
        
        #self.momentum.eval()
        self.potential.eval()
        t_extract_list = []
        Z_extract_list = []
        accept_list = []
        #num_steps = np.random.randint(self.num_steps_min, self.num_steps_max + 1)

        Z_t = prior_z.clone().detach()
        
        gamma = 1.*self.gamma
        #print(f'Initial lr: {gamma}')
        for t in range(T):
            if sample_chain and t > 0 and t % thinning == 0:
                t_extract_list.append(t)
                Z_extract_list.append(Z_t.clone().detach().cpu())
                accept_list.append(1.)

            # reset computation graph
            Z_t = self.euler(Z_t,self.grad_potential,sampler,gamma=gamma)
            #Z_t,acc_prob = hasing_metropolis(Z_new, V_new, Z_t, V_t, self.potential,self.momentum.log_prob, U)
            # only if extracting the samples so we have a sequence of samples
            if t>0 and t%200==0:
                gamma *=0.1
                print('decreasing lr for sampling')

            #print('iteration: '+ str(t))
        if not sample_chain:
            return Z_t.clone().detach(),1.
        return t_extract_list, Z_extract_list, accept_list


    def euler(self,x,grad_x,sampler,gamma=1e-2):
        x_t = x.clone().detach()
        D = np.sqrt(gamma)
        x_t = x_t - gamma / 2 * grad_x(x_t) + D * sampler.sample()
        return x_t

class SphereLangevinSampler(object):
    def __init__(self, potential, T=100,  gamma=1e-2):          
        
        self.potential = potential
        
        #self.num_steps_min = num_steps_min
        #self.num_steps_max = num_steps_max
        self.gamma = gamma
        self.grad_potential = Grad_potential(self.potential)
        self.T = T
        #self.grad_momentum = Grad_potential(self.momentum.log_prob)
        #self.sampler_momentum = momentum_sampler 
        
    def sample(self,prior_z,sample_chain=False,T=None,thinning=10):
        if T is None:
            T = self.T
        sampler = torch.distributions.Normal(torch.zeros_like(prior_z), 1.)
        
        #self.momentum.eval()
        self.potential.eval()
        t_extract_list = []
        Z_extract_list = []
        accept_list = []
        #num_steps = np.random.randint(self.num_steps_min, self.num_steps_max + 1)

        Z_t = prior_z.clone().detach()
        
        gamma = 1.*self.gamma
        #print(f'Initial lr: {gamma}')
        for t in range(T):
            if sample_chain and t > 0 and t % thinning == 0:
                t_extract_list.append(t)
                Z_extract_list.append(Z_t.clone().detach().cpu())
                accept_list.append(1.)

            # reset computation graph
            Z_t = self.euler(Z_t,self.grad_potential,sampler,gamma=gamma)
            #Z_t,acc_prob = hasing_metropolis(Z_new, V_new, Z_t, V_t, self.potential,self.momentum.log_prob, U)
            # only if extracting the samples so we have a sequence of samples
            if t>0 and t%200==0:
                gamma *=0.1
                print('decreasing lr for sampling')

            #print('iteration: '+ str(t))
        if not sample_chain:
            return Z_t.clone().detach(),1.
        return t_extract_list, Z_extract_list, accept_list


    def euler(self,x,grad_x,sampler,gamma=1e-2):
        x_t = x.clone().detach()
        D = np.sqrt(2.*gamma)
        R = x_t.shape[1]
        grad = gamma * grad_x(x_t) 
        dot = torch.sum(grad*x_t, dim=1)
        #grad = grad -   torch.einsum('n,nd->nd',dot,x_t)/np.sqrt(R)
        x_t = x_t - grad + D * sampler.sample()
        return x_t


class DOT(object):
    def __init__(self, potential, T=100,  gamma=1e-2):          
        
        self.potential = potential
        
        #self.num_steps_min = num_steps_min
        #self.num_steps_max = num_steps_max
        self.gamma = gamma
        self.grad_potential = Grad_potential(self.potential)
        self.T = T
        self.init_latent = None
        self.init_prior = None
        #self.grad_momentum = Grad_potential(self.momentum.log_prob)
        #self.sampler_momentum = momentum_sampler 
    
    def sample(self,prior_z,sample_chain=False,T=None,thinning=10):
        if T is None:
            T = self.T
        sampler = torch.distributions.Normal(torch.zeros_like(prior_z), 1.)
        reg = torch.ones_like(prior_z)
        #self.momentum.eval()
        self.potential.eval()
        t_extract_list = []
        Z_extract_list = []
        accept_list = []
        #num_steps = np.random.randint(self.num_steps_min, self.num_steps_max + 1)
        assert len( prior_z.shape )==2
        Z_t = prior_z[:,0].clone().detach()
        self.init_prior = prior_z[:,1].clone().detach()
        
        gamma = 1.*self.gamma
        #print(f'Initial lr: {gamma}')
        for t in range(T):
            if sample_chain and t > 0 and t % thinning == 0:
                t_extract_list.append(t)
                Z_extract_list.append(Z_t.clone().detach().cpu())
                accept_list.append(1.)

            # reset computation graph
            Z_t = self.update(Z_t,gamma=gamma)
            #Z_t,acc_prob = hasing_metropolis(Z_new, V_new, Z_t, V_t, self.potential,self.momentum.log_prob, U)
            # only if extracting the samples so we have a sequence of samples
            if t>0 and t%200==0:
                gamma *=0.1
                print('decreasing lr for sampling')

            #print('iteration: '+ str(t))
        if not sample_chain:
            return Z_t.clone().detach(),1.
        return t_extract_list, Z_extract_list, accept_list


    def update(self,x,gamma=1e-2, eps = 1e-3):
        x_t = x.clone().detach()
        D = np.sqrt(gamma)
        R = x_t.shape[1]
        x_t.requires_grad_()
        prox = torch.norm(x_t - self.init_prior.data + eps, dim=1)
        out = self.potential(x_t).sum() + prox.sum()
        out.backward()

        grad =  x_t.grad
        dot = torch.sum(grad*x_t, dim=1)
        #grad = grad -   torch.einsum('n,nd->nd',dot,x_t)/np.sqrt(R)
        x_t = x_t - gamma*grad
        return x_t



class MALA(object):
    def __init__(self, potential, T=100,  gamma=1e-2):          
        
        self.potential = potential
        
        #self.num_steps_min = num_steps_min
        #self.num_steps_max = num_steps_max
        self.gamma = gamma
        self.grad_potential = Grad_potential(self.potential)
        self.T = T
        #self.grad_momentum = Grad_potential(self.momentum.log_prob)
        #self.sampler_momentum = momentum_sampler 
        
    def sample(self,prior_z,sample_chain=False,T=None,thinning=10):
        if T is None:
            T = self.T
        sampler = torch.distributions.Normal(torch.zeros_like(prior_z), 1.)
        
        #self.momentum.eval()
        self.potential.eval()
        t_extract_list = []
        Z_extract_list = []
        accept_list = []
        #num_steps = np.random.randint(self.num_steps_min, self.num_steps_max + 1)
        U  =  torch.zeros([prior_z.shape[0]]).to(prior_z.device)
        Z_t = prior_z.clone().detach()
        old_grad = self.grad_potential(Z_t)
        gamma = 1.*self.gamma
        for t in range(T):
            if sample_chain and t > 0 and t % thinning == 0:
                t_extract_list.append(t)
                Z_extract_list.append(Z_t.clone().detach().cpu())
                accept_list.append(1.)
            U = U.uniform_(0,1)
            # reset computation graph
            Z_new, new_grad, correction = self.euler(Z_t,old_grad,self.grad_potential,sampler,gamma=gamma)
            Z_t,old_grad,acc_prob = self.hasing_metropolis(Z_new, Z_t, new_grad, old_grad, self.potential,correction, U)
            # only if extracting the samples so we have a sequence of samples
            # if t>0 and t%200==0:
            #     gamma *=0.1
            #     print('decreasing lr for sampling')

            #print('iteration: '+ str(t))
        if not sample_chain:
            return Z_t.clone().detach(), acc_prob.mean().item()
        return t_extract_list, Z_extract_list, accept_list


    def euler(self,x,old_grad,grad_x,sampler,gamma=1e-2):
        
        D = np.sqrt(2.*gamma)
        noise = sampler.sample()
        x_t = x - gamma * old_grad + D * noise
        x_t = x_t.clone().detach()
        new_grad = grad_x(x_t)

        err = x - x_t + gamma*new_grad
        correction = 0.5*torch.sum(noise**2, dim=1) - 1./4*gamma*torch.sum(err**2, dim=1)

        return x_t, new_grad, correction

    def hasing_metropolis(self,Z_new, Z_0,new_grad, old_grad, potential,correction, U):
        with torch.no_grad():
            potential_0 = potential(Z_0)
            potential_new = potential(Z_new)

        H0 = potential_0
        H  = potential_new
        difference = -H + H0 + correction
        acc_prob = torch.exp(-F.relu(-difference))
        accepted = U < acc_prob
        Z_out = 1.*Z_0
        grad_out = 1.* old_grad
        Z_out[accepted] = 1.* Z_new[accepted]
        grad_out[accepted] = 1.* new_grad[accepted]
        return Z_out, grad_out,acc_prob

class TruncLangevinSampler(object):
    def __init__(self, potential, momentum, trunc=2., sample_chain = False, T=100, num_steps_min=10, num_steps_max=20, gamma=1e-2,kappa = 4e-2):          
        
        self.momentum = momentum
        self.potential = potential
        
        self.num_steps_min = num_steps_min
        self.num_steps_max = num_steps_max
        self.kappa = kappa
        self.gamma = gamma
        self.sample_chain = sample_chain
        self.trunc = trunc
        self.grad_potential = Grad_cond_potential(self.potential)
        self.T = T
        #self.grad_momentum = Grad_potential(self.momentum.log_prob)
        #self.sampler_momentum = momentum_sampler 
        
    def sample(self,prior_z,sample_chain=False,T=None,thinning=10):
        if T is None:
            T = self.T
        labels = prior_z[1]
        sampler = torch.distributions.Normal(torch.zeros_like(prior_z[0]), 1.)
        
        #self.momentum.eval()
        self.potential.eval()
        t_extract_list = []
        Z_extract_list = []
        accept_list = []
        num_steps = np.random.randint(self.num_steps_min, self.num_steps_max + 1)

        Z_t = prior_z[0].clone().detach()
        gamma = self.gamma
        for t in range( T):
            # reset computation graph
            Z_t = self.euler(Z_t,labels,self.grad_potential,sampler,gamma=gamma)
            #Z_t,acc_prob = hasing_metropolis(Z_new, V_new, Z_t, V_t, self.potential,self.momentum.log_prob, U)
            # only if extracting the samples so we have a sequence of samples
            if t>0 and t%200==0:
                gamma *=0.1
                print('decreasing lr for sampling')
            if sample_chain and thinning != 0 and t % thinning == 0:
                t_extract_list.append(t)
                X_t  = Z_t.clone().detach().cpu(), labels
                Z_extract_list.append(X_t)
                accept_list.append(1.)
            #print('iteration: '+ str(t))
        if not sample_chain:
            return Z_t.clone().detach()
        return t_extract_list, Z_extract_list, accept_list


    def euler(self,x,labels,grad_x,sampler,gamma=1e-2):
        x_t = x.clone().detach()
        D = np.sqrt(gamma)
        x_t = x_t - gamma / 2 * grad_x(x_t,labels) + D * sampler.sample()
        if self.trunc>0.:
            x_t = -F.relu(self.trunc-x_t) + self.trunc
            x_t = F.relu(x_t+self.trunc) - self.trunc
        return x_t



class MetropolisHastings(object):
    def __init__(self, potential, sample_chain = False, T=100,gamma=1e-2):          
        
        self.potential = potential

        self.sample_chain = sample_chain
        self.T = T
        self.gamma = gamma
        
    def sample(self,prior_z,sample_chain=False,T=None,thinning=10):
        if T is None:
            T = self.T

        self.potential.eval()
        proposal_sampler = torch.distributions.Normal(torch.zeros_like(prior_z), 1.)
        #proposal_sampler = torch.distributions.Normal(torch.zeros_like(prior_z), 1.)
        #U_sampler = torch.distributions.Uniform(0, 1)
        U  =  torch.zeros([prior_z.shape[0]]).to(prior_z.device)
        samples = []
        t_extract_list = []
        accept_list = []
        z_cur = prior_z
        potential_cur = self.potential(prior_z)
        gamma= self.gamma
        acc_prob = torch.ones_like(U)
        with torch.no_grad():
            for t in range(T):
                if sample_chain and thinning != 0 and t % thinning == 0:
                    samples.append(z_cur.clone().detach().cpu())
                    accept_list.append(acc_prob.mean().item())
                    t_extract_list.append(t)

                z_prop = z_cur +np.sqrt(gamma)*proposal_sampler.sample()
                U = U.uniform_(0,1)
                z_cur,  acc_prob = self.hasing_metropolis(z_prop, z_cur,self.potential, U)

        if not sample_chain:
            return z_cur.clone().detach(), acc_prob.mean().item()
        return t_extract_list, samples, accept_list


    def hasing_metropolis(self,Z_new, Z_0, potential,U):
        potential_0 = potential(Z_0)
        potential_new = potential(Z_new)
        H0 = potential_0
        H  = potential_new
        difference = -H + H0
        acc_prob = torch.exp(-F.relu(-difference))
        accepted = U < acc_prob
        Z_out = 1.*Z_0
        Z_out[accepted] = 1.* Z_new[accepted]
        return Z_out, acc_prob


class IndependentMetropolisHastings(object):
    def __init__(self, potential, sample_chain = False, T=100, gamma=1e-2):          
        
        self.potential = potential
        self.sample_chain = sample_chain
        self.T = T
        self.gamma = gamma
        
    def sample(self,prior_z,sample_chain=False,T=None,thinning=10):
        if T is None:
            T = self.T

        self.potential.eval()
        proposal_sampler = torch.distributions.Normal(torch.zeros_like(prior_z), 1.)
        #proposal_sampler = torch.distributions.Normal(torch.zeros_like(prior_z), 1.)
        #U_sampler = torch.distributions.Uniform(0, 1)
        U  =  torch.zeros([prior_z.shape[0]]).to(prior_z.device)
        samples = []
        t_extract_list = []
        accept_list = []
        z_cur = prior_z
        potential_cur = self.potential(prior_z)
        gamma =1.*self.gamma
        acc_prob = torch.ones_like(U)
        with torch.no_grad():

            for t in range(T):
                if sample_chain and thinning != 0 and t % thinning == 0:
                    samples.append(z_cur.clone().detach().cpu())
                    accept_list.append(acc_prob.mean().item())
                    t_extract_list.append(t)
                z_prop = proposal_sampler.sample()
                #potential_prop = self.potential(z_prop)
                U = U.uniform_(0,1)
                z_cur,  acc_prob = self.hasing_metropolis(z_prop, z_cur,self.potential, U)

        if not sample_chain:
            return z_cur.clone().detach(), acc_prob.mean().item()
        return t_extract_list, samples, accept_list


    def hasing_metropolis(self,Z_new, Z_0, potential,U):
        potential_0 = potential(Z_0)
        potential_new = potential(Z_new)


        H0 = potential_0
        H  = potential_new
        difference = -H + H0
        acc_prob = torch.exp(-F.relu(-difference))
        accepted = U < acc_prob
        Z_out = 1.*Z_0
        Z_out[accepted] = 1.* Z_new[accepted]
        return Z_out, acc_prob


class ContrastiveDivergenceSampler(nn.Module):
    def __init__(self,noise_gen, sampler):
        self.buffer = None
        self.max_buffer = 10000
        self.buffer_cursor = 0
        self.noise_gen = noise_gen
        self.sampler = sampler
        self.mask_int = None
        self.T = 10
    def sample_buffer(self,N):
        if self.buffer is None:
            self.buffer = self.noise_gen.sample([self.max_buffer]).to('cpu')
        self.mask_int =torch.multinomial(torch.ones(self.buffer.shape[0]),N, replacement=True).to(self.buffer.device)
        return self.buffer[self.mask_int,:].to(self.device)        
        
    def sample(self,data):
        prior_samples = self.sample_buffer(data.shape[0])
        gen_data_in,_ = self.sampler.sample(prior_samples,sample_chain=False, T=self.T).detach()
        self.buffer[self.mask_int,:] = gen_data_in.cpu()
        return gen_data_in

