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
class VocalSaparateAPIView(APIView):
	permission_classes = [IsAuthenticated]
	def post(self, request, format=None):
		
		song_file = request.data.get('song_url', None)
		music_file = request.data.get('music_url', None)
		if not None in [song_file, music_file]:
			vocal_url = perform_vocal_separate(song_file, music_file)
			if not vocal_url == 'NoURL':
				return Response({"message":"Vocal ready to use.", "vocal_url": vocal_url, "code":200})
			else:
				return Response({"message":"Music or Song Url is not correct.",  "code": 500})
		else:
			return Response({"message":"Please provide all required parameters.", "code": 402})

	

class PitchGuideAPIView(APIView):
	permission_classes = [AllowAny]
	def post(self, request, format=None):
		filename=  "music1.mp3"
		try:
			music_file = request.data.get('song_url', None)
			difference = request.data.get('difference', 2)
			wget.download(music_file, filename)
			downsample = 1
			samplerate = 44100 // downsample

			win_s = 4096 // downsample 
			hop_s = 512  // downsample
			duration_samplerate = 0
			duration_win_s = 512
			duration_hop_s = duration_win_s // 2 

			s = source(filename, samplerate, hop_s)
			o = onset("default", win_s, hop_s, duration_samplerate)

			samplerate = s.samplerate

			tolerance = 0.8

			pitch_o = pitch("yin", win_s, hop_s, samplerate)
			pitch_o.set_unit("midi")
			pitch_o.set_tolerance(tolerance)
			initial_training =[]
			total_frames = 0
			
			while True:
			    samples, read = s()
			    pitch1 = pitch_o(samples)[0]
			    confidence = 0#np.nan_to_num(pitch_o.get_confidence())
			    if o(samples):
			    	confidence = np.nan_to_num(o.get_last_s())
			    if confidence > 0:
			    	initial_training.append({"start_time": str(total_frames / float(samplerate)) ,"durations": str(confidence),"value": str(pitch1)})
			    total_frames += read
			    if read < hop_s: break

			with open(os.path.join(settings.BASE_DIR, settings.STATIC_ROOT, 'static/picth_file/pitch-guide.json'), "w") as file:
				file.write(json.dumps(initial_training))
                        cloud_pitch = cloudinary.uploader.upload(os.path.join(settings.BASE_DIR, settings.STATIC_ROOT, 'static/picth_file/pitch-guide.json'),resource_type="raw")

			os.remove(filename)
			return Response({"message":"Pitch guide success.", "code":200,"revised_pitch": cloud_pitch['url'] })
		except Exception as e:
			print(e)
			os.remove(filename)
			return Response({"message":"Something went wrong", "code":500})


def perform_vocal_separate(*args, **kwargs):
	try:
		VOICE_FILE_PATH = 'vocal.mp3'
		song_file = "song.mp3"
		music_file = "music.mp3"
		wget.download(args[0], song_file)
		wget.download(args[1], music_file)
		
		SECONDS = librosa.get_duration(filename=song_file)
		mixed, sr = librosa.load(song_file,
			mono=True, 
			duration=SECONDS)

		music, _ = librosa.load(music_file,
			mono=True,
			duration=SECONDS)
		voice = mixed -  music
		librosa.output.write_wav(VOICE_FILE_PATH, voice,sr)
		os.remove(song_file)
		os.remove(music_file)
		return VOICE_FILE_PATH
	except Exception as e:
		raise e
		return "NoURL"
