from django.db import models


class Subject(models.Model):
    name = models.CharField(max_length=50)
    state = models.CharField(max_length=20)  # awake, REM, NREM


class Recording(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    brain_region = models.CharField(max_length=50)  # Hippocampus, V1 …
    probe_type = models.CharField(max_length=50)  # Neuropixels, Tetrode
