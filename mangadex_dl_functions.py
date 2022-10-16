# Copyright (c) 2019-2021 eli fessler
# Copyright (C) 2022 Uwuewsky
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import urllib.request, os, time, re, json, shutil, zipfile, concurrent.futures
from collections import deque

class DownloadLimits:
	last_requests = deque(maxlen=5)
	
	def check():
		if len(DownloadLimits.last_requests) == 5:
			# if less than second since last 5 requests
			interval = time.time() - DownloadLimits.last_requests[0]
			if interval < 1:
				time.sleep(1 - interval)
		DownloadLimits.last_requests.append(time.time())

def url_request(url):
	# let's try five times
	error = None
	for i in range(0,5):
		try:
			DownloadLimits.check()
			response = urllib.request.urlopen(url, timeout=60).read()
			return response
		except Exception as err:
			error = err
			time.sleep(2)
	raise error

def get_json(url):
	return json.loads(url_request(url).decode("utf-8"))

def get_uuid(manga_url):
	regex = re.compile("\w{8}-\w{4}-\w{4}-\w{4}-\w{12}")
	manga_uuid_match = re.findall(regex, manga_url)
	if manga_uuid_match:
		return manga_uuid_match[0]
	else:
		raise ValueError("Cannot retrieve manga UUID")

def get_title(manga_uuid, language):
	response = get_json("https://api.mangadex.org/manga/{}".format(manga_uuid))
	
	title_en = response["data"]["attributes"]["title"]["en"]
	title = title_en
	
	if language in response["data"]["attributes"]["title"]:
		title = response["data"]["attributes"]["title"][language]
	else:
		for altTitle in response["data"]["attributes"]["altTitles"]:
			if language in altTitle:
				title = altTitle[language]
	return title, title_en

def get_chapters_info(manga_uuid, language):
	return get_json("https://api.mangadex.org/manga/{}/feed"\
			"?limit=0&translatedLanguage[]={}"\
			"&contentRating[]=safe"\
			"&contentRating[]=suggestive"\
			"&contentRating[]=erotica"\
			"&contentRating[]=pornographic"
			.format(manga_uuid, language))

def get_chapters_list(manga_uuid, total_chapters, language):
	chapters_list = []
	offset = 0
	while offset < total_chapters: # if more than 500 chapters!
		response = get_json("https://api.mangadex.org/manga/{}/feed"\
				    "?order[volume]=asc&order[chapter]=asc&limit=500"\
				    "&translatedLanguage[]={}&offset={}"\
				    "&contentRating[]=safe"\
				    "&contentRating[]=suggestive"\
				    "&contentRating[]=erotica"\
				    "&contentRating[]=pornographic"
				    .format(manga_uuid, language, offset))
		chapters_list += response["data"]
		offset += 500
	return chapters_list

def get_scanlation_group_info(group_id):
	return get_json("https://api.mangadex.org/group/{}".format(group_id))["data"]

def print_available_chapters(chapters_list):
	print("Available chapters: (total {})".format(len(chapters_list)), end="")
	volume_number = None
	for chapter in chapters_list:
		chapter_volume = chapter["attributes"]["volume"] if chapter["attributes"]["volume"] != "" and chapter["attributes"]["volume"] != None else "Unknown"
		chapter_name = chapter["attributes"]["chapter"] if chapter["attributes"]["chapter"] != None else "Oneshot"
		
		if volume_number != chapter_volume:
			volume_number = chapter_volume
			print("\nVolume {:2}".format(volume_number), end=": ")
		
		print("{:>6}".format(chapter_name), end="")
	print()

def get_duplicated_chapters(chapters_list):
	duplicated_chapters_list = []
	
	check_list = chapters_list.copy()
	for chapter_i in check_list:
		duplicates_list = []
		for chapter_j in check_list:
			if chapter_i["id"] == chapter_j["id"]:
				continue
			if chapter_i["attributes"]["volume"] == chapter_j["attributes"]["volume"] and \
			   chapter_i["attributes"]["chapter"] == chapter_j["attributes"]["chapter"]:
				if chapter_i not in duplicates_list:
					duplicates_list.append(chapter_i)
				if chapter_j not in duplicates_list:
					duplicates_list.append(chapter_j)
		duplicated_chapters_list.append(duplicates_list)
		if chapter_i in check_list:
			check_list.remove(chapter_i)
	
	return duplicated_chapters_list

def resolve_duplicated_chapters(chapters_list, duplicated_chapters_list, resolve):
	if resolve == None:
		resolve = input("Specify what to do with duplicate chapters.\n"\
				"   all  - download all available chapters\n"\
				"   one  - download only one chapter\n"\
				"<other> - manually specify scanlate groups priority\n"\
				"> ")
		print()
	if resolve == "all":
		return chapters_list
	if resolve == "one":
		for duplicated_chapters in duplicated_chapters_list:
			first = True
			for duplicated_chapter in duplicated_chapters:
				if first:
					first = False
				else:
					if duplicated_chapter in chapters_list:
						chapters_list.remove(duplicated_chapter)
		return chapters_list
	
	def get_chapter_scanlation_id(chapter):
		for relation in chapter["relationships"]:
			if relation["type"] == "scanlation_group":
				return(relation["id"])
	
	print("Receiving scanlate groups info...\n")
	scanlation_groups_id = set()
	scanlation_groups = []
	
	for duplicated_chapters in duplicated_chapters_list:
		for duplicated_chapter in duplicated_chapters:
			group_id = get_chapter_scanlation_id(duplicated_chapter)
			if group_id != None:
				scanlation_groups_id.add(group_id)
	
	for group_id in scanlation_groups_id:
		scanlation_groups.append(get_scanlation_group_info(group_id))
	
	print("Duplicate chapters have {} scanlate groups".format(len(scanlation_groups)))
	for group in scanlation_groups:
		group_priority = input("Specify priority for {}. [1-5]\n> ".format(group["attributes"]["name"]))
		group["attributes"]["priority"] = group_priority
	print("Groups are prioritized\n")
	scanlation_groups.sort(key=lambda x: x["attributes"]["priority"])
	
	for duplicated_chapters in duplicated_chapters_list:
		max_priority = "6"
		prior_chapter = None
		for duplicated_chapter in duplicated_chapters:
			chapter_scanlate_id = get_chapter_scanlation_id(duplicated_chapter)
			for group in scanlation_groups:
				if chapter_scanlate_id == group["id"] and group["attributes"]["priority"] < max_priority:
					prior_chapter = duplicated_chapter
		for duplicated_chapter in duplicated_chapters:
			if duplicated_chapter != prior_chapter and duplicated_chapter in chapters_list:
				chapters_list.remove(duplicated_chapter)
	
	return chapters_list

def parse_range(range_input):
	requested_list = []
	# Sample object: 
	# sample = {"start": {"volume": 2, "chapter": 5}, | v2(5)-v6(9)
	#             "end": {"volume": 6, "chapter": 9}} |
	
	if range_input == "all":
		return "all"
	
	# split the input into separate ranges
	entry_input_list = range_input.split(",")
	
	# define a start and end point for each range
	for entry_input in entry_input_list:
		range_object = {"start": {"volume": None, "chapter": None}, "end": {"volume": None, "chapter": None}}
		
		volume_input_list = entry_input.split("-")
		
		# compose a range object from points 
		start = True
		for volume_input in volume_input_list:
			if volume_input == "":
				break
			# parse volume number
			re_entry = "v(u|\d+)"
			regex = re.compile("{}".format(re_entry))
			volume_list = re.findall(regex, volume_input)
			
			if len(volume_list) != 0:
				if start:
					range_object["start"]["volume"] = volume_list[0]
				else:
					range_object["end"]["volume"] = volume_list[0]
			
			# parse chapter number
			re_entry = "\((Oneshot|[\d.]+)\)"
			regex = re.compile("{}".format(re_entry))
			chapter_input = re.findall(regex, volume_input)
			
			if len(chapter_input) != 0:
				for chapter_ranges in chapter_input[0].split(","):
					re_entry = "(Oneshot|[\d.]+)"
					regex = re.compile("{}".format(re_entry))
					chapter = re.findall(regex, chapter_ranges)[0]
					if "-" in chapter_ranges:
						chapter = (tuple(chapter_ranges.split("-")))
					if start:
						range_object["start"]["chapter"] = chapter
					else:
						range_object["end"]["chapter"] = chapter
			
			start = False
		requested_list.append(range_object)
	
	return requested_list

def get_requested_chapters(chapters_list, dl_list):
	if dl_list == "all":
		return chapters_list
	
	requested_chapters = []
	for dl_range in dl_list:
		is_in_range = False     # flag to add chapters
		chapter_last = None     # flags to add last chapter
		is_chapter_last = False
		volume_last = None      # flags to add last volume
		is_volume_last = False
		for chapter in chapters_list:
			chapter_volume = chapter["attributes"]["volume"]
			chapter_name   = chapter["attributes"]["chapter"] if chapter["attributes"]["chapter"] != None else "Oneshot"
			
			# checking exit conditions
			is_volume_last = True if chapter_volume != volume_last and volume_last != None else False
			is_chapter_last = True if chapter_name != chapter_last and chapter_last != None else False
			
			# if it was the last volume or chapter
			if (volume_last != None and is_volume_last) or (chapter_last != None and is_chapter_last):
				break
			
			# range start point check
			if (chapter_volume == None and dl_range["start"]["volume"] == "u") or \
			   (chapter_volume == dl_range["start"]["volume"]):
				if dl_range["end"]["volume"] == None:
					volume_last = chapter_volume
				if chapter_name == dl_range["start"]["chapter"] or \
				   dl_range["start"]["chapter"] == None:
					# flag this chapters to add in list
					is_in_range = True
					if dl_range["end"]["volume"] == None and dl_range["start"]["chapter"] != None:
						chapter_last = chapter_name
			# range end point check
			if (chapter_volume == None and dl_range["end"]["volume"] == "u") or \
			   (chapter_volume == dl_range["end"]["volume"]):
				# this volume is the last 
				volume_last = chapter_volume
				if chapter_name == dl_range["end"]["chapter"]:
					chapter_last = chapter_name
			
			# add chapter to list
			if is_in_range:
				requested_chapters.append(chapter)
	return requested_chapters

def download_chapters(requested_chapters, directory_name, is_datasaver):
	chapter_count = 1
	chapter_count_max = len(requested_chapters)
	
	for chapter in requested_chapters:
		chapter_number = chapter["attributes"]["chapter"] if chapter["attributes"]["chapter"] != None else "Oneshot"
		chapter_name = chapter["attributes"]["title"] if chapter["attributes"]["title"] != None else ""
		chapter_volume = chapter["attributes"]["volume"] if chapter["attributes"]["volume"] != None else "Unknown"
		
		print("\nDownloading chapter [{:3}/{:3}] Ch.{} {}".format(chapter_count, chapter_count_max, chapter_number, chapter_name))
		
		chapter_json = get_json("https://api.mangadex.org/at-home/server/{}".format(chapter["id"]))
		base_url = "{}/{}/{}/".format(chapter_json["baseUrl"], "data-saver" if is_datasaver else "data", chapter_json["chapter"]["hash"])
		image_url_list = chapter_json["chapter"]["dataSaver"] if is_datasaver else chapter_json["chapter"]["data"]
		
		directory_chapter = os.path.join(directory_name, "Volume {}".format(chapter_volume), "Chapter {}".format(chapter_number))
		if os.path.exists(directory_chapter):
			# name folders like "Chapter 1 (2)"
			for i in range(1, 10):
				temp_path = "{} ({})".format(directory_chapter, i)
				if not os.path.exists(temp_path):
					directory_chapter = temp_path
					break
		os.makedirs(directory_chapter)

		image_count = 1
		image_count_downloaded = 1
		image_count_max = len(image_url_list)
		future_list = []
		with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
			for image_url in image_url_list:
				future_list.append(executor.submit(download_image, base_url + image_url, image_count, directory_chapter))
				image_count += 1
			for future in concurrent.futures.as_completed(future_list):
				print("\r  Downloaded images [{:3}/{:3}]...".format(image_count_downloaded, image_count_max), end="")
				image_count_downloaded += 1
		chapter_count += 1
	print("\nChapters download completed successfully")

def download_image(full_url, image_count, directory_chapter):
	image_file_path = os.path.join(directory_chapter, "{:03d}{}".format(image_count, os.path.splitext(full_url)[1]))
	image_file = open(image_file_path, mode="wb")
	with image_file:
		image_file.write(url_request(full_url))

def archive_manga_directory(manga_directory, archive_mode, is_keep):
	print("\nArchive downloaded chapters...")
	
	directory_list = []
	
	if archive_mode == "manga":
		# archive whole manga directory
		directory_list.append(manga_directory)
	elif archive_mode == "vol":
		# archive volume directories
		directory_list += map(lambda d: os.path.join(manga_directory, d), next(os.walk(manga_directory))[1])
	else:
		for volume_dir in os.listdir(manga_directory):
			volume_dir_path = os.path.join(manga_directory, volume_dir)
			if os.path.isdir(volume_dir_path):
				# archive chapter directories
				directory_list += map(lambda d: os.path.join(volume_dir_path, d), next(os.walk(volume_dir_path))[1])

	# skip directories that have already been archived before
	directory_list = list(filter(lambda x: not os.path.exists(x + ".zip"), directory_list))
	
	directory_count_archived = 1
	directory_count_max = len(directory_list)
	for directory in directory_list:
		archive_directory(directory, is_keep)
		print("\r  Archiving [{:3}/{:3}]...".format(directory_count_archived, directory_count_max), end="")
		directory_count_archived += 1
	print("\nArchiving completed successfully")

def archive_directory(directory, is_keep):
	archive_format = "zip" # you can change that to cbz
	zip_name = "{}.{}".format(directory, archive_format)
	
	with zipfile.ZipFile(zip_name, mode="w", compression=zipfile.ZIP_STORED, allowZip64=True) as zip_file:
		for root, dirs, files in os.walk(directory):
			for file in files:
				filename = os.path.join(root, file)
				arcname = os.path.relpath(os.path.join(root, file), directory)
				zip_file.write(filename, arcname)
	if not is_keep:
		shutil.rmtree(directory)

def dl(manga_url, args):
	print("\nReceiving manga's info...")
	manga_uuid = get_uuid(manga_url)
	manga_title, manga_title_en = get_title(manga_uuid, args.language)
	
	print("\n[{:2}/{:2}] TITLE: {}\n".format(args.manga_urls.index(manga_url)+1, len(args.manga_urls), manga_title))
	
	# check available chapters
	chapters_info = get_chapters_info(manga_uuid, args.language)
	
	if chapters_info["total"] == 0:
		raise ValueError("No chapters available to download!")
	
	chapters_list = get_chapters_list(manga_uuid, chapters_info["total"], args.language)
	
	# duplicate check
	if args.resolve != "all":
		duplicated_chapters_list = get_duplicated_chapters(chapters_list)
		if len(duplicated_chapters_list) != 0:
			chapters_list = resolve_duplicated_chapters(chapters_list, duplicated_chapters_list, args.resolve)
	
	# print chapters list
	print_available_chapters(chapters_list)
	
	# i/o for chapters to download
	if args.download == None:
		dl_input = input("\nEnter chapter(s) to download:"\
				 "\n(see README for examples of valid format)"\
				 "\n> ")
	else:
		dl_input = args.download
	
	dl_list = parse_range(dl_input)
	
	# requested chapters list in dl_range
	requested_chapters = get_requested_chapters(chapters_list, dl_list)
	if len(requested_chapters) == 0:
		raise ValueError("Empty list of chapters. Make sure you enter the correct download range!")

	# download images
	if os.path.isdir(args.outdir):
		out_directory = args.outdir
	else:
		out_directory = "."
	
	manga_directory = os.path.join(out_directory, manga_title_en)
	if not os.path.exists(manga_directory):
		try:
			os.makedirs(manga_directory)
		except OSError:
			manga_directory = os.path.join(out_directory, "Manga {}".format(manga_uuid))
			if not os.path.exists(manga_directory):
				os.makedirs(manga_directory)
	download_chapters(requested_chapters, manga_directory, args.datasaver)
	
	# archive
	if args.archive != None:
		archive_manga_directory(manga_directory, args.archive, args.keep)
	
	print("\nManga \"{}\" was successfully downloaded".format(manga_title))
