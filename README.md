# Anqa

Anqa is a data standard for time-frequency annotated wildlife sound files. An example can be found [here](https://www.kaggle.com/datasets/ollypowell/nz-wild-sound)

The goal for this project is to encourage regional institutions to produce and share strongly labelled regional datasets, to a common standard, enabling better regional models and local capacity building.

## Principles

* **Tabular** annotation format
* **Metadata first** - One row per audio file, including lat, long in WGS84 coordinates and a date-time stamp in ISO 8601.  The metadata should follow any files subsequently derived from the source files.
* **Labels stored in a separate file**, with one row per label, with a many to one relationship with the metadata file, matching by relative file name.
* **e-bird** labels for birds, defaulting to **inaturalist** codes where no e-bird label is available
* **Every animal** sound must get a time-frequency box.  Where the species can not be identified, fall back to a higher taxonomic order.  For example insects should use 47158.
* **A naming schema** matching the above codes to what ever local scheme is to be used, plus the scientific name
* **An 'unknown' label** for any wildlife sound that can not be identified.
* **Original source filename**, start-stop time within, and sampling rate are tracked through subsequent sub sampling
* **Modularity** - It should be possible to merge any two datasets programatically, whilst keeping the above properties
* **Open Source** CC-BY licence, where no licence already exists for a given row-item in the metadata

Whilst open-sourcing the training data, regional institutions should also be encouraged to make careful use of their time/date/location metadata to create and hold back independent test sets for model selection and calibration.

By creating models that also predict time-frequency boxes in the same format, we enable efficient data reviewing, model calibration, and continuous improvement of the datasets through human-in-loop review in a single unified format.

<img src=".//images/anqa_diagram.png" width="900">


## Motivation

This work has come out of development of the *Kaytoo* model for the Department of Conservation (New Zealand).  The source data for that project came in multiple formats, some could not be used at all, whilst the rest were initially converted to the format used by Xeno-Canto and BirdCLEF.  That format labels presence/absence of species for arbitrary length sound crops.  The model predictions for BirdCLEF models are segment level (5-second) multi-label presence-absence.

The Xeno-Canto and Inaturalist arbitrary length formats have a number of shortcomings: 

* It was inefficient trying to deliver any continuous improvement to the training dataset by reviewing the short crops.  It is much faster the reviewer to look at a fixed length (1-minute) soundscape with a suitable visualisation tool, and confirm or edit multiple annotations.  If short crops are needed for model training they can easily be extracted programatically.

* It is hard to build strong models from training on the inherently weak-labelling in the Xeno-Canto data.  A large proportion of this data contains false negatives, whilst the training routine has no way to ensure sub-sampling contains sound the expected classes, leading to false positives during training.

On the output side, segment level model predictions also have some shortcommings:

* Working with the fixed-segment-length data is hard to visualise and inconvenient for deriving meaningful statistical insights for monitoring.

* The training data is incomparable to model predictions, making it hard to perform any meaningful form of model calibration from data in it's short-crop form.

The value-proposition here is for regional institutions to use their own experts to create and time-frequency box annotated datasets.  Then for the rest of time a world-leading model architecture is just a code-fork away, whilst the training dataset can be continuously reviewed and improved.

## Proposed Columns

This is still work-in progress, but for now the columns in use are derived from those used in the Raven .selections.txt tables, as well as the BirdCLEF metadata files.  Additional columns have been added, for example to identify what reviewing (if any) has taken place, or if detection models were used to assist the labelling.
