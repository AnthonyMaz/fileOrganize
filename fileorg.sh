#!/bin/bash

### Image File Types:

###Adobe Photoshop - (.PSD),GIMP - (.XCF), Adobe Illustrator - (.AI), CorelDRAW - (.CDR) (.tif, .tiff),(.bmp),(.jpg, .jpeg),(.gif),(.png),(.eps),RAW Image Files (.raw, .cr2, .nef, .orf, .sr2)

IMAGES=$( (find . -iname '*.jpg' -o -iname '*.png' -o -iname '*.jpeg' -o -iname '*.gif' -o -iname '*.giff' -o -iname '*.tiff' -o -iname '*.tif' -o -iname '*.xfc' -o -iname '*.ai' -o -iname '*.cdr' -o -iname '*.eps' -o -iname '*.raw' -o -iname '*.cr2' -o -iname '*.nef' -o -iname '*.orf' -o -iname '*.sr2')> images.txt )




$(mkdir images)
#$(mkdir {Images,Videos,Documents,NoExtension})


#while true; do

	#IMGTXT=./images.txt
	while read LINE; do
			for i in ${LINE}
			do
				if [ $i == sha1sum of ${LINE} ]  ##compare shasum files in list to other files in list
					then
					# cp dupes to dupes dir under main dir	
				fi

			done

		mv -v ${LINE} ./images
	done < ./images.txt
###use for  with an array to go to 




#	for i in $IMGTXT
#	do
#		$(cp -v $IMGTXT ./images) 
#	done

#done
