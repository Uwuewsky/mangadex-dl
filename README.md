![Screenshot](screenshot.gif)

# mangadex-dl
A Python package to download manga from [MangaDex.org](https://mangadex.org/).

## Requirements
  * [Python 3.11+](https://www.python.org/downloads/)
  * [requests\[socks\] 2.28+](https://pypi.org/project/requests/)
  * [PyMuPDF 1.25+](https://pypi.org/project/PyMuPDF/)
  * [natsort 8.4+](https://pypi.org/project/natsort/)
  * [tomlkit 0.13+](https://pypi.org/project/tomlkit/)

## Installation & usage
```bash
$ git clone https://github.com/Uwuewsky/mangadex-dl
$ cd mangadex-dl/
$ pip install -r requirements.txt
$ ./start.py
# or
$ python3 -m mangadex_dl [manga_urls]
```

## Features

### Download manga from MangaDex.org
Search for manga by title or by UUID.

### Configuration
You can configure the default settings via `config.toml` or via the GUI.

### Archiving to ZIP, CBZ or PDF
Your downloaded manga is stored as individual images, but you can optionally make an archive or PDF document after downloading. Specify in the settings in what form you want to archive (individual chapters, individual volumes or the whole manga). Also specify the format/extension (zip, cbz, pdf). A table of contents is also created for PDF.

The archiving function can be used via `-a` argument: `$ python -m mangadex_dl -a dir1/ dir2/ ...`. The path should be the root directory of the manga, i.e. not the path to an volume or chapter.

*Note*: this function archives the entire manga directory, not just the chapters you downloaded in this session. Specify a different output directory in the settings before downloading if you don't need it.

### Download chapters from a specific scanlate group
If the same chapter is uploaded by multiple groups, you can download all available chapters, download only one version, or manually filter the groups based on priority. Set the desired group to the highest priority, and the chapter from that group will be downloaded if possible.

### GUI and console mode
By default, mangadex_dl opens in GUI mode. Set `gui = false` in `config.toml` to open in console mode, which together with `download = all` can be useful for non-interactive downloads. Manga links can be specified as `$ python -m mangadex_dl url1 url2 ...` or via the file `$ python -m mangadex_dl < list.txt`, where `list.txt` contains the URL/UUID on a separate line.

## Example usage

### Console version:

Here are some examples of valid downloading range input:
* `v1`: Download all volume 1;
* `v1(3)`: Download chapter 3 from volume 1;
* `v1-v5`: Download volumes 1-5;
* `v1(3)-v5`: Download from chapter 3 to volume 5;
* `v1(3)-v5(66)`: Download from chapter 3 to chapter 66;
* `v1,v4-v5,v8(99)`: Can be combined with a comma;
* `vu`: Some chapters do not have a volume. Therefore, they appear in vu (Volume Unknown);
* `vu(Oneshot)`: Download oneshot;
* `all`: Download whole manga.

Also some examples of INVALID input:
* `1,2,3`: Obsolete format;
* `v1(1,2,3-6)`: You cannot specify more than one chapter in parentheses, use the example above.

```
$ python3 -m mangadex_dl

Enter URL or text to search by title. (leave blank to complete)
> yotsuba

Enter URL or text to search by title. (leave blank to complete)
> 

Receiving manga's info...
The following titles were found on request:
 1. Yotsuba&! (2003) by Azuma Kiyohiko
 2. Mahouka Koukou no Rettousei - Yotsuba Keishou-hen (2020) by Satou Tsutomu
 3. Try! Try! Try! (2001) by Azuma Kiyohiko
 4. Kimi ni, Yotsuba (2018) by Akino Kabocha
 
Insert number (leave blank to cancel):
> 1

[ 1/ 1] TITLE: Yotsuba&!

Available chapters: (total 119)
Volume 1 :      1     2     3     4     5     6     7
Volume 2 :      8     9    10    11    12    13    14
Volume 3 :     15    16    17    18    19    20    21
Volume 4 :     22    23    24    25    26    27  27.5
Volume 5 :     28    29    30    31    32    33    34
Volume 6 :     35    36    37    38    39    40    41
Volume 7 :     42    43    44    45    46    47    48
Volume 8 :     49    50    51    52    53    54  54.2    55
Volume 9 :     56    57    58    59    60    61    62
Volume 10:     63    64    65    66    67    68    69  69.2
Volume 11:     70    71    72    73    74    75    76
Volume 12:     77    78    79  79.2    80    81  81.2  81.3    82
Volume 13:     83    84    85    86    87    88    89    90
Volume 14:     91    92    93    94    95    96    97
Volume 15:     98    99   100 100.2   101 101.2   102 102.2   103   104 104.2
Volume Unknown:    105   106   107   108   109

Enter chapters to download:
(see README for examples of valid format) (leave blank to cancel)
> v15(103)-v15(104.2)

Downloading chapter [  3/  3] Ch.104.2 Yotsuba & Backpacks (part 2)
  Downloaded images [ 32/ 32]...
Chapters download completed successfully

Archive downloaded chapters...
  Archiving [  3/  3]...
Archiving completed successfully

Manga "Yotsuba&!" was successfully downloaded
```

## License
[GPLv3](https://www.gnu.org/licenses/gpl-3.0.html)
