#!/usr/bin/env python3

# coding: utf-8

from keras.models import load_model
from keras_contrib.layers import InstanceNormalization
import dasher.deep.metrics
import sys
import os

in_model = sys.argv[1]
model_name = sys.argv[2]

custom_objects = {'dice_coefficient_loss': dasher.deep.metrics.dice_coefficient_loss,
                  'dice_coefficient': dasher.deep.metrics.dice_coefficient,
                  'dice_coef': dasher.deep.metrics.dice_coef,
                  'dice_coef_loss': dasher.deep.metrics.dice_coef_loss,
                  'weighted_dice_coefficient': dasher.deep.metrics.weighted_dice_coefficient,
                  'weighted_dice_coefficient_loss': dasher.deep.metrics.weighted_dice_coefficient_loss,
                  "InstanceNormalization": InstanceNormalization}

model = load_model(in_model, custom_objects=custom_objects)
model_json = model.to_json() 

with open("%s.json" % model_name, "w") as json_file:
    json_file.write(model_json)

print("Saving model weights")

model.save_weights('%s_weights.h5' % model_name)

print("Model weights and json saved")
