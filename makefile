rsgain_release != curl -s https://api.github.com/repos/complexlogic/rsgain/releases | jq -r '.[].assets[].browser_download_url' | grep -e "rsgain_[0-9.]*_$(dpkg --print-architecture)" | head -n 1
tmp_file != mktemp

install:
	sudo apt install -y --no-install-recommends ffmpeg

	curl -s -L $(rsgain_release) -o $(tmp_file)
	sudo dpkg --install $(tmp_file)
	rm $(tmp_file)

	sudo cp *.py /usr/local/bin
