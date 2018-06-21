from rest_framework.views import APIView
from rest_framework.permissions import (AllowAny, IsAuthenticated)
from rest_framework.response import Response
import librosa
import soundfile as sf
import io
import wget
import os
import math
import sys
import numpy as np
from numpy.linalg import norm, svd
from aubio import source, pitch, onset
from pydub import AudioSegment
from vocal_separator import settings
import scipy;
import cloudinary
import json
from decimal import Decimal
from numpy.linalg import norm, svd
from django.core.files.uploadedfile import TemporaryUploadedFile

def handle_uploaded_file(song_input_file, path):
    with open(path, 'wb+') as destination:
        for chunk in song_input_file.chunks():
            destination.write(chunk)

class PitchGuideAPIView(APIView):
	permission_classes = [AllowAny]
	def post(self, request, format=None):
		root_path =  os.path.join(settings.BASE_DIR, settings.STATIC_ROOT, 'static/picth_song')
		files = os.listdir(root_path)
		for item in files:
			os.remove(os.path.join(root_path, item))

		difference = request.data.get('difference', 1)
		is_vocal = True if request.data.get('type') == 'voice' else False
		
		from separate_vocal.separateLead import get_vocal_file
		song_input_file = request.data.get('song_input_file')
		if type(song_input_file) is TemporaryUploadedFile:
			song_input_file = request.FILES.get('song_input_file')
			filename = os.path.join(settings.BASE_DIR, settings.STATIC_ROOT, 'static/picth_song/'+song_input_file.name)
			handle_uploaded_file(song_input_file, filename)
			song_name = song_input_file.name
		else:
			filename = os.path.join(settings.BASE_DIR, settings.STATIC_ROOT, 'static/picth_song/'+song_input_file.split('/')[-1])
			wget.download(song_input_file, filename)
			song_name = song_input_file.split('/')[-1]

		voc_output_file = '/'.join(filename.split('/')[:-1])+'/'+'_vocal_'+filename.split('/')[-1]
		mus_output_file = '/'.join(filename.split('/')[:-1])+'/'+'_music_'+filename.split('/')[-1]
		pitch_output_file = '/'.join(filename.split('/')[:-1])+'/'+'_pitch_'+filename.split('/')[-1]
		options = {
			        'song_input_file': filename,
			        'voc_output_file': voc_output_file,
			        'mus_output_file': mus_output_file, 
			        'pitch_output_file': pitch_output_file, 
			        'verbose': request.data.get('verbose', True), 
			        'separateSignals': request.data.get('separateSignals', True), 
			        'nbiter': request.data.get('nbiter', 30), 
			        'windowSize': request.data.get('windowSize', 0.04644), 
			        'fourierSize': request.data.get('fourierSize', None), 
			        'hopsize': request.data.get('hopsize', 0.0058), 
			        'R': request.data.get('R', 40.0), 
			        'melody': request.data.get('melody', None), 
			        'P_numAtomFilters': request.data.get('P_numAtomFilters', 30), 
			        'K_numFilters': request.data.get('K_numFilters', 10), 
			        'minF0': request.data.get('minF0', 100.0), 
			        'maxF0': request.data.get('maxF0', 800.0), 
			        'stepNotes': request.data.get('stepNotes', 2)
			    }
		if len([i for i in options if options[i] == '']) > 0:
			return  Response({"message":"Please remove empty field or provide value", "code":500})
		get_vocal_file(options)


		try:
			downsample = 1
			samplerate = 44100 // downsample
			win_s = 4096 // downsample
			hop_s = 512  // downsample
			s = source(voc_output_file, samplerate, hop_s)
			samplerate = s.samplerate
			tolerance = 0.8
			pitch_o = pitch("yin", win_s, hop_s, samplerate)
			pitch_o.set_unit("midi")
			pitch_o.set_tolerance(tolerance)
			initial_training =[]
			total_frames = 0
			end_time = 0
			idx = 1
			while True:
				samples, read = s()
				pitch_value = pitch_o(samples)[0]
				start_time = total_frames / float(samplerate)
				duration = start_time-end_time
				end_time = start_time
				initial_training.append({"id": idx, "start_time": str(start_time) ,"durations": str(duration),"value": str(pitch_value)})
				total_frames += read
				idx +=1
				if read < hop_s: break

			temp_val = 0
			temp_ids = []

			for idx, val in enumerate(initial_training):
				value = Decimal(val['value'])
				if value != 0 and abs(Decimal(initial_training[idx]['value']) - value) < difference:
					temp_ids.append(val['id'])
					temp_val +=value
				else:
					avg = scipy.mean(temp_val)
					if len(temp_ids) > 0:
						for j in initial_training:
							if j['id'] in temp_ids:
								j['value']=str(avg)
					temp_val = 0
					temp_ids = []
			
			with open(os.path.join(settings.BASE_DIR, settings.STATIC_ROOT, 'static/picth_file/{}.json'.format(song_name)), "w") as file:
				file.write(json.dumps(initial_training))
			cloud_pitch = cloudinary.uploader.upload(os.path.join(settings.BASE_DIR, settings.STATIC_ROOT, 'static/picth_file/{}.json'.format(song_name)),resource_type="raw")
			return Response({"message":"Pitch guide success.", "code":200,"revised_pitch": cloud_pitch['url'] })
		except Exception as e:
			print(e)
			return Response({"message":"Something went wrong", "code":500})



class VocalSaparateAPIView(APIView):
	permission_classes = [AllowAny]
	def post(self, request, format=None):
		root_path =  os.path.join(settings.BASE_DIR, settings.STATIC_ROOT, 'static/picth_song')
		files = os.listdir(root_path)
		for item in files:
			os.remove(os.path.join(root_path, item))

		from separate_vocal.separateLead import get_vocal_file
		song_input_file = request.data.get('song_input_file')
		if type(song_input_file) is TemporaryUploadedFile:
			song_input_file = request.FILES.get('song_input_file')
			filename = os.path.join(settings.BASE_DIR, settings.STATIC_ROOT, 'static/songs/'+song_input_file.name)
			handle_uploaded_file(song_input_file, filename)
		else:
			filename = os.path.join(settings.BASE_DIR, settings.STATIC_ROOT, 'static/songs/'+song_input_file.split('/')[-1])
			wget.download(song_input_file, filename)
		voc_output_file = '/'.join(filename.split('/')[:-1])+'/'+'_vocal_'+filename.split('/')[-1]
		mus_output_file = '/'.join(filename.split('/')[:-1])+'/'+'_music_'+filename.split('/')[-1]
		pitch_output_file = '/'.join(filename.split('/')[:-1])+'/'+'_pitch_'+filename.split('/')[-1]
		options = {
			        'song_input_file': filename,
			        'voc_output_file': voc_output_file,
			        'mus_output_file': mus_output_file, 
			        'pitch_output_file': pitch_output_file, 
			        'verbose': request.data.get('verbose', True), 
			        'separateSignals': request.data.get('separateSignals', True), 
			        'nbiter': request.data.get('nbiter', 30), 
			        'windowSize': request.data.get('windowSize', 0.04644), 
			        'fourierSize': request.data.get('fourierSize', None), 
			        'hopsize': request.data.get('hopsize', 0.0058), 
			        'R': request.data.get('R', 40.0), 
			        'melody': request.data.get('melody', None), 
			        'P_numAtomFilters': request.data.get('P_numAtomFilters', 30), 
			        'K_numFilters': request.data.get('K_numFilters', 10), 
			        'minF0': request.data.get('minF0', 100.0), 
			        'maxF0': request.data.get('maxF0', 800.0), 
			        'stepNotes': request.data.get('stepNotes', 2)
			    }
		if len([i for i in options if options[i] == '']) > 0:
			return  Response({"message":"Please remove empty field or provide value", "code":500})
			
		get_vocal_file(options)
		file_path=  'http://localhost:8000/static/songs/'+'_vocal_'+filename.split('/')[-1]
		return Response({"message":"Vocal separation completed.", 'vocal_file': file_path, "code": 200})