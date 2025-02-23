# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import Callable, Optional

from torch import Tensor
from torchmultimodal.diffusion_labs.predictors.predictor import Predictor
from torchmultimodal.diffusion_labs.schedules.discrete_gaussian_schedule import (
    DiscreteGaussianSchedule,
)


class VPredictor(Predictor):
    """Given a model that's trained to predict v and corresponding schedule,
    this class computes the predicted noise and x0 at step t. V is an interpolation
    between x0 and noise designed to keep the prediciton target stable as Signal
    to Noise (SNR) ratio varies through the diffusion process. V is first proposed
    in "Progressive Distillation for Fast Sampling of Diffusion Models" by Salimans
    and Ho (https://arxiv.org/abs/2202.00512).

    Attributes:
        schedule (DiffusionSchedule): defines diffusion of noise through time
        clamp_func (Callable): function to clamp prediction values
    """

    def __init__(
        self, schedule: DiscreteGaussianSchedule, clamp_func: Optional[Callable] = None
    ):
        self.clamp_func = clamp_func
        self.schedule = schedule

    def predict_x0(self, prediction: Tensor, xt: Tensor, t: Tensor) -> Tensor:
        shape, dtype = xt.shape, xt.dtype
        x_coef = self.schedule("sqrt_alphas_cumprod", t, shape)
        v_coef = self.schedule("sqrt_compliment_alphas_cumprod", t, shape)
        x0 = x_coef * xt - v_coef * prediction
        if self.clamp_func is not None:
            x0 = self.clamp_func(x0)
        return x0.to(dtype)

    def predict_noise(self, prediction: Tensor, xt: Tensor, t: Tensor) -> Tensor:
        shape, dtype = xt.shape, xt.dtype
        x_coef = self.schedule("sqrt_recip_alphas_cumprod", t, shape)
        e_coef = self.schedule("sqrt_recip_alphas_cumprod_minus_one", t, shape)
        x0 = self.predict_x0(prediction, xt, t)
        e = (x_coef * xt - x0) / e_coef
        return e.to(dtype)
