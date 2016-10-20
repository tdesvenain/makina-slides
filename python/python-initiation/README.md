# HOWTO

## landslide
    
    mkvirtualenv landslide
    pip install landslide
    pip install watchdog  # for watching mode

## prince for pdf generation

    wget https://www.princexml.com/download/prince_10r7-1_ubuntu16.04_amd64.deb
    sudo dpkg -i prince_10r7-1_ubuntu16.04_amd64.deb

## generate slides

    landslide syntaxe-bases.cfg

## generate pdf

    landslide syntaxe-bases-pdf.cfg
