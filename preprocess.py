import csv
import numpy as np
import cv2
import tables
import os
import sys

def normalize_grayscale(image_data):
    """
    Normalize the image data with Min-Max scaling to a range of [0.1, 0.9]
    :param image_data: The image data to be normalized
    :return: Normalized image data
    """
    img_max = np.max(image_data)
    img_min = np.min(image_data)
    a = -0.5
    b = 0.5

    img_normed = a + (b-a)*(image_data - img_min)/(img_max - img_min)
    #print(np.max(img_normed))
    #print(np.min(img_normed))
    return img_normed

def normalize_color(image_data):
    """
    Normalize the image data on per channel basis. 
    """
    img_normed_color = np.zeros_like(image_data, dtype=float)
    for ch in range(image_data.shape[3]):
        tmp = normalize_grayscale(image_data[:,:,:,ch])
        img_normed_color[:,:,:,ch] = tmp
    #print(np.max(img_normed_color))
    #print(np.min(img_normed_color))
    return img_normed_color

# Below func. copied from: https://chatbotslife.com/using-augmentation-to-mimic-human-driving-496b569760a9#.kgjn97cup
def augment_brightness_camera_images(image):
    cv2.imwrite("ori.png", image)
    image1 = cv2.cvtColor(image,cv2.COLOR_RGB2HSV)
    #random_bright = .25+np.random.uniform()
    random_bright = .25
    #print(random_bright)
    image1[:,:,2] = image1[:,:,2]*random_bright
    image1 = cv2.cvtColor(image1,cv2.COLOR_HSV2RGB)
    cv2.imwrite("after.png", image1)
    return image1

def add_random_shadow(image):
    top_y = 320*np.random.uniform()
    top_x = 0
    bot_x = 160
    bot_y = 320*np.random.uniform()
    image_hls = cv2.cvtColor(image,cv2.COLOR_RGB2HLS)
    shadow_mask = 0*image_hls[:,:,1]
    X_m = np.mgrid[0:image.shape[0],0:image.shape[1]][0]
    Y_m = np.mgrid[0:image.shape[0],0:image.shape[1]][1]
    
    shadow_mask[((X_m-top_x)*(bot_y-top_y) -(bot_x - top_x)*(Y_m-top_y) >=0)]=1
    #random_bright = .25+.7*np.random.uniform()
    if np.random.randint(2)==1:
        random_bright = .5
        cond1 = shadow_mask==1
        cond0 = shadow_mask==0
        if np.random.randint(2)==1:
            image_hls[:,:,1][cond1] = image_hls[:,:,1][cond1]*random_bright
        else:
            image_hls[:,:,1][cond0] = image_hls[:,:,1][cond0]*random_bright    
    image = cv2.cvtColor(image_hls,cv2.COLOR_HLS2RGB)
    return image

# -------------------------------------
# Command line argument processing
# -------------------------------------
if len(sys.argv) < 2:
    print("Missing training data file.")
    print("python3 model.py <data.h5> [flip]")

DATA_DIR = str(sys.argv[1])

FLIP_ON = False
if len(sys.argv)==3:
    FLIP_ON = True

# ------------------
# Read data from recorded dataset
# ------------------

# List to store data read from recording
X_train = []
y_train = []
throttle = []
brake = []
speed = []

SMALL_SCALE = 0.9
LARGE_SCALE = 1.1

with open(DATA_DIR+'/driving_log.csv', newline='') as f:
    reader = csv.reader(f)
    for row in reader:
        if row[0] != 'center':
            # center
            # image input, crop and scale
            img = cv2.imread(DATA_DIR+"/"+row[0])
            img_crop = img[56:160,:,:]
            img_resize = cv2.resize(img_crop, (200,66))
            img_resize = add_random_shadow(img_resize)
            # Opencv bgr to rgb
            img_resize = img_resize[...,::-1]
            angle = np.float32(row[3])
            X_train.append(img_resize)
            y_train.append(angle)
            # throttle, brake, speed
            row_4 = np.float32(row[4])
            row_5 = np.float32(row[5])
            row_6 = np.float32(row[6])
            throttle.append(row_4)
            brake.append(row_5)
            speed.append(row_6)

            # Scale angle a bit for left/right images
            if angle > 0: # right turn
                l_angle = LARGE_SCALE * angle
                r_angle = SMALL_SCALE * angle
            else: # left turn
                l_angle = SMALL_SCALE * angle
                r_angle = LARGE_SCALE* angle

            # left
            img = cv2.imread(DATA_DIR+"/"+row[1])
            img_crop = img[56:160,:,:]
            img_resize = cv2.resize(img_crop, (200,66))
            img_resize = add_random_shadow(img_resize)
            # Opencv bgr to rgb
            img_resize = img_resize[...,::-1]
            X_train.append(img_resize)
            y_train.append(l_angle)
            throttle.append(row_4)
            brake.append(row_5)
            speed.append(row_6)

            # right
            img = cv2.imread(DATA_DIR+"/"+row[2])
            img_crop = img[56:160,:,:]
            img_resize = cv2.resize(img_crop, (200,66))
            img_resize = add_random_shadow(img_resize)
            # Opencv bgr to rgb
            img_resize = img_resize[...,::-1]
            X_train.append(img_resize)
            y_train.append(r_angle)
            throttle.append(row_4)
            brake.append(row_5)
            speed.append(row_6)
    print("Original data read done.")

    # Horizontal flipping
    if FLIP_ON:
      # Roll back to beginning of file
      f.seek(0)
      for row in reader:
        if row[0] != 'center':
            img = cv2.imread(DATA_DIR+"/"+row[0])
            img_crop = img[56:160,:,:]
            img_resize = cv2.resize(img_crop, (200,66))
            img_resize = add_random_shadow(img_resize)
            angle = np.float32(row[3])
            # Horizontally flipped version of the image
            img_resize_flip = cv2.flip(img_resize,0)
            # Opencv bgr to rgb
            img_resize_flip = img_resize_flip[...,::-1]
            X_train.append(img_resize_flip)
            y_train.append(-angle)
            row_4 = np.float32(row[4])
            row_5 = np.float32(row[5])
            row_6 = np.float32(row[6])
            throttle.append(row_4)
            brake.append(row_5)
            speed.append(row_6)

            if angle > 0: # right turn
                l_angle = LARGE_SCALE * angle
                r_angle = SMALL_SCALE * angle
            else: # left turn
                l_angle = SMALL_SCALE * angle
                r_angle = LARGE_SCALE* angle

            # left
            img = cv2.imread(DATA_DIR+"/"+row[1])
            img_crop = img[56:160,:,:]
            img_resize = cv2.resize(img_crop, (200,66))
            img_resize = add_random_shadow(img_resize)
            # Horizontally flipped version of the image
            img_resize_flip = cv2.flip(img_resize,0)
            # Opencv bgr to rgb
            img_resize_flip = img_resize_flip[...,::-1]
            X_train.append(img_resize_flip)
            y_train.append(-l_angle)
            throttle.append(row_4)
            brake.append(row_5)
            speed.append(row_6)

            # right
            img = cv2.imread(DATA_DIR+"/"+row[2])
            img_crop = img[56:160,:,:]
            img_resize = cv2.resize(img_crop, (200,66))
            img_resize = add_random_shadow(img_resize)
            # Horizontally flipped version of the image
            img_resize_flip = cv2.flip(img_resize,0)
            # Opencv bgr to rgb
            img_resize_flip = img_resize_flip[...,::-1]
            X_train.append(img_resize_flip)
            y_train.append(-r_angle)
            throttle.append(row_4)
            brake.append(row_5)
            speed.append(row_6)
      print("Horizontal flipping done.")

# sanity check
# Opencv: rgb back to bgr
img_resize = X_train[23]
img_resize = img_resize[...,[2,1,0]]
cv2.imwrite("preprocessing_sanity_chk.png", img_resize)

# Convert to numpy array
X_train = normalize_color(np.array(X_train))
y_train = np.array(y_train)
throttle = np.array(throttle)
brake = np.array(brake)
speed = np.array(speed)

#print("max X_train = ", np.max(X_train))
#print("min X_train = ", np.min(X_train))
#print("y_train = ", y_train)
print("Total samples: ", len(y_train))

# -------------------
# Save to HDF5 file
# -------------------
h5_file = DATA_DIR+".h5"
if not os.path.isfile(h5_file):
    print('Saving preprocessed data to HDF5 file...', h5_file)
    try:
        with tables.open_file(h5_file, 'w') as f:
            filters = tables.Filters(complevel=5, complib='blosc')

            f_img = f.create_earray(f.root, 'img', tables.Atom.from_dtype(X_train[0].dtype), shape=(0,X_train.shape[1],X_train.shape[2],X_train.shape[3]), filters=filters, expectedrows=X_train.shape[0])
            #f_img = f.create_earray(f.root, 'img', tables.Atom.from_dtype(X_train[0].dtype), shape=(0,66,200,3), filters=filters, expectedrows=len(X_train))
            f_steer = f.create_earray(f.root, 'steer', tables.Atom.from_dtype(np.dtype('float')), shape=(0,), filters=filters)
            f_throttle = f.create_earray(f.root, 'throttle', tables.Atom.from_dtype(np.dtype('float')), shape=(0,), filters=filters)
            f_brake = f.create_earray(f.root, 'brake', tables.Atom.from_dtype(np.dtype('float')), shape=(0,), filters=filters)
            f_speed = f.create_earray(f.root, 'speed', tables.Atom.from_dtype(np.dtype('float')), shape=(0,), filters=filters)

            f_img.append(X_train)
            f_steer.append(y_train)
            f_throttle.append(throttle)
            f_brake.append(brake)
            f_speed.append(speed)

            f.close()

    except Exception as e:
        print('Unable to save data to', h5_file, ':', e)
        raise
else:
    print('File existing, NO UPDATE to:', h5_file)


