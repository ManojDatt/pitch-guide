from django.db import models

# Create your models here.
class Document(models.Model):
	document = models.FileField(blank=False,null=False)

