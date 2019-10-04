#!/usr/bin/env python3

# coding: utf-8

import os
import nibabel as nib
import numpy as np

from keras.models import load_model, model_from_json
from keras_contrib.layers import InstanceNormalization
from hippmapper.deep.metrics import (dice_coefficient, dice_coefficient_loss, dice_coef, dice_coef_loss,
                                      weighted_dice_coefficient_loss, weighted_dice_coefficient)
import warnings

warnings.simplefilter("ignore", RuntimeWarning)
warnings.simplefilter("ignore", FutureWarning)

os.environ['TF_CPP_MIN_LOG_LEVEL'] = "3"


def load_old_model_json(model_json):
    print("\n loading pre-trained model")

    custom_objects = {'dice_coefficient_loss': dice_coefficient_loss, 'dice_coefficient': dice_coefficient,
                      'dice_coef': dice_coef, 'dice_coef_loss': dice_coef_loss,
                      'weighted_dice_coefficient': weighted_dice_coefficient,
                      'weighted_dice_coefficient_loss': weighted_dice_coefficient_loss}
    try:
        custom_objects["InstanceNormalization"] = InstanceNormalization
    except ImportError:
        pass

    try:
        return model_from_json(model_json, custom_objects=custom_objects)
    except ValueError as error:
        if 'InstanceNormalization' in str(error):
            raise ValueError(str(error) +
                             "\n\n Please install keras-contrib for InstanceNormalization:\n"
                             "'pip install git+https://www.github.com/keras-team/keras-contrib.git'")
        else:
            raise error


def get_prediction_labels(prediction, threshold=0.5, labels=None):
    n_samples = prediction.shape[0]
    label_arrays = []

    for sample_number in range(n_samples):
        label_data = np.argmax(prediction[sample_number], axis=0) + 1
        label_data[np.max(prediction[sample_number], axis=0) < threshold] = 0
        if labels:
            for value in np.unique(label_data).tolist()[1:]:
                label_data[label_data == value] = labels[value - 1]
        label_arrays.append(np.array(label_data, dtype=np.uint8))

    return label_arrays


def prediction_to_image(prediction, affine, label_map=False, threshold=0.5, labels=None):
    if prediction.shape[1] == 1:
        data = prediction[0, 0]

    elif prediction.shape[1] > 1:
        if label_map:
            label_map_data = get_prediction_labels(prediction, threshold=threshold, labels=labels)
            data = label_map_data[0]
        else:
            return multi_class_prediction(prediction, affine)
    else:
        raise RuntimeError("Invalid prediction array shape: {0}".format(prediction.shape))

    return nib.Nifti1Image(data, affine)


def multi_class_prediction(prediction, affine):
    prediction_images = []

    for i in range(prediction.shape[1]):
        prediction_images.append(nib.Nifti1Image(prediction[0, i], affine))

    return prediction_images


def run_test_case(test_data, model_json, model_weights, affine,
                  output_label_map=False, threshold=0.5, labels=None):
    json_file = open(model_json, 'r')
    loaded_model_json = json_file.read()
    json_file.close()
    model = load_old_model_json(loaded_model_json)

    model.load_weights(model_weights)

    prediction = model.predict(test_data)

    return prediction_to_image(prediction, affine, label_map=output_label_map, threshold=threshold,
                               labels=labels)
