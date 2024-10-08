# HippMapp3r

*HippMapp3r* (pronounced hippmapper) is a CNN-based segmentation algorithm of the whole hippocampus
using MRI images from BrainLab.
It can deal with brains with extensive atrophy and segments the hippocampi in seconds.
It uses a T1-weighted image as the only input and segments skull-stripped images.
Note: skull-stripping is a required preprocessing step if the skull is present.

We recommend using HippMapp3r with the Docker or Singularity containers we provide, since support for local installs has been discontinued. See our doc: [installation instructions](https://hippmapp3r.readthedocs.io/en/latest/docker.html) for more information.

<p align="center">
      <img src="docs/images/graph_abstract.png" alt="hippocampus pop-up window"
      width="600" height="200"/>
</p>


____________________________

For more details, see our [docs](https://hippmapp3r.readthedocs.io).

Copyright (C) 2019 AICONSlab.
