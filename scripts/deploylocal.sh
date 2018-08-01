PROJECT_DIR="~/TokenDroplet"
SOURCE_DIR="${PROJECT_DIR}/src/ScanService"

if [ ! -e "$SOURCE_DIR" ]; then
    mkdir -p "${PROJECT_DIR}/src"
    cd "${PROJECT_DIR}/src"
    echo "clone ScanService.git ..."
    git clone https://gitee.com/metaverse/ScanService.git
fi

for i in "$@"; do

TARGET_PATH="${PROJECT_DIR}/$i"
echo "deploy $i to ${TARGET_PATH}";
mkdir -p ${TARGET_PATH}
cp -r "$SOURCE_DIR" "$TARGET_PATH"

done

