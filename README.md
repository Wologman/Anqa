# Anqa

Anqa is a data standard for time-frequency annotated wildlife sound files. An example can be found [here](https://www.kaggle.com/datasets/ollypowell/nz-wild-sound). Also the latest working example of the annotation notebook, together with some sample data can be found [here](https://filedn.eu/l1723vRFnsquJMoK85UThX0/Anqa_Annotate_Notebook/).

The goal for this project is to encourage regional institutions to produce and share strongly labelled regional datasets, to a common standard, enabling better regional models and local capacity building.

## Principles

* **Tabular** annotation format
* **Metadata first** - One row per audio file, including lat, long in WGS84 coordinates and a date-time stamp in ISO 8601.  The metadata should follow any files subsequently derived from the source files.
* **Labels stored in a separate file**, with one row per label, with a many to one relationship with the metadata file, matching by relative file name.
* **e-bird** labels for birds, defaulting to **inaturalist** codes where no e-bird label is available
* **Every animal** sound (plus any other class that may be useful) must get a time-frequency box.  Where the species can not be identified, fall back to a higher taxonomic order.  For example insects should use 47158.  Where no inaturalist code exists fall back to lower case in English, no underscores.  eg 'chainsaw', 'helicopter', 'boat', 'vehicle'.
* **A naming schema** matching the above codes to what ever local scheme is to be used, plus the scientific name
* **An 'unknown' label** for any wildlife sound that can not be identified.
* **Original source filename**, start-stop time within, and sampling rate are tracked through subsequent chunking or resampling
* **Modularity** - It should be possible to merge any two datasets programatically, whilst keeping the above properties
* **Open Source** CC-BY licence, where no licence already exists for a given row-item in the metadata

Whilst open-sourcing the training data, regional institutions should also be encouraged to make careful use of their date-time-location metadata to create and hold back independent test sets for model selection and calibration.

By creating models that also predict time-frequency boxes in the same format, we enable efficient data reviewing, model calibration, and continuous improvement of the datasets through human-in-loop review in a single unified format.

<img src=".//images/anqa_diagram.png" width="900">


## Motivation

This work has come out of development of the *Kaytoo* model for the Department of Conservation (New Zealand).  The source data for that project came in multiple formats, some could not be used at all, whilst the rest were initially converted to the format used by Xeno-Canto and BirdCLEF.  That format labels presence/absence of species for arbitrary length sound crops.  The model predictions for BirdCLEF models are segment level (5-second) multi-label presence-absence.

The Xeno-Canto and Inaturalist arbitrary length formats have a number of shortcomings: 

* It it is inefficient trying to deliver any continuous improvement to the training dataset by reviewing the short crops.  It is much faster the reviewer to look at a fixed length (1-minute) soundscape with a suitable visualisation tool, and confirm or edit multiple annotations.  If short crops are needed for model training they can easily be extracted programatically.

* It is hard to build strong models from training on the inherently weak-labelling in the Xeno-Canto data.  A large proportion of this data contains false negatives, whilst the training routine has no way to ensure sub-sampling contains sound the expected classes, leading to false positives during training.

On the model output side, segment-level predictions also have some shortcommings:

* The fixed-segment-length predictions introduce a quantisation effect that removes or distorts any concept of bird abundance.  This distortion is different by species due to differing call lengths and frequency.

* The annotated data is incomparable to model predictions, making it hard to perform model calibration.

The value-proposition here is for regional institutions to use their own experts to create and time-frequency box annotated datasets.  Then for the rest of time a world-leading model architecture is just a code-fork away.  At the same time the training and test datasets can be continuously reviewed and improved as an integral part of model calibration from ongoing fieldwork.

## Proposed Columns

This is still work-in progress, but for now the columns in use are derived from those used in the Raven .selections.txt tables, as well as the BirdCLEF metadata files.  Additional columns have been added, for example to identify what reviewing (if any) has taken place, or if detection models were used to assist the labelling.

For the `metadata.parquet` file the meaning of the fields is described in more detail below:

| Field | Value | Data Type | Discription
|---|---|---|---|
| filename | 20190831_074504_from_0.flac | string | Filepath relative to the top level `audio` folder |
| collection | NPCP | string | Short name identifying a project or source the data came from |
| primary_label | riflem1 | string |(Optional) As with Xeno-canto format, the most prominent bird in the sample |
| secondary_labels | [nezbel1] | [list-string] | As with Xeno-canto format, less prominent birds |
| url |https://example.com | string | Any public repository that can link to this exact sample |
| latitude | -41.32 | float  |  Latitude of the recording in WGS84 (EPSG:4326)
| longitude | 173.29 | float |  Longitude of the recording in WGS84 (EPSG:4326)
| author | Mr Bigglesworth |  string |  Name of the original annotator |
| licence | CC BY 4.0 | string |  Licence, ideally CC BY 4.0  |
| recorded_on | 2022-10-22 07:45:04 |  string  |  Recording date-time in ISO 8601
| reviewed_on | 2023-10-22 |  string  |  Last time the file was reviewed (or originally labelled). Date-time in ISO 8601
| source_filename | 20190831_074504.wav | string  |  Relative filepath of the original recording
| source_sr_khz | 32 | float | Original source sampling rate
| source_start_s | 0 | float | Start time for this sample relative to source recording start
| source_end_s | 60 | float | End time for this sample relative to source recording start
| source_device | AR4 | string  |  Individual device unique ID if avaliable, otherwise model name
| models_used | BirdNet v3.0 |  string | List any ML models used to label this sample  

<br>

For the `annotations.parquet`:


| Field | Value | Data Type | Discription
|---|---|---|---|
| Filename | 20190831_074504_from_0.flac  | string | Filepath relative to the top level `audio` folder |
|Start Time (s) |  4.3 | float |  Start of bounding box relative to start of sample
| End Time (s) | 8.2 |  float |  End of bounding box relative to start of sample
| Low Freq (Hz) | 9728  |  float |  Bottom of bounding box in Hz
| High Freq (Hz) | 11184 | float |  Top of bounding box in Hz
| Label | riflem1 | string | eBird, with fallbacks as described above
| Type | song  | string |  Any of: {call, song, alarm, duet, begging, flight call, echolocation, other} or leave empty
| Sex | m  |  string  |  Any of: {m, f} or leave empty
| Score |  0.7  | float |  Confidence of the annotation label between 0 and 1
| Life Stage |  juvenile | string |  Any of: {juvenile, adault} or leave empty
| Indv ID |  some_uid  | string  |  A unique identfier for an individual animal
| Delta Time (s) | float |  3.9  |  Derived from End Time (s) - Start Time (s)
| Delta Freq (Hz) | float | 1456  |  Derived from High Freq (Hz) - End Time (Hz)
| Avg Power Density (dB FS/Hz) |  float |  -60.4 |  Calculated from STFT for values within the bounding box