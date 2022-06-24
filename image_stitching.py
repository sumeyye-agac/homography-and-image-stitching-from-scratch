from PIL import Image
import numpy as np
import math
from matplotlib import pyplot as plt

# 1. Selecting corresponding points
def selectingPoints(input_path_image_source, input_path_image_dest, image_source, image_dest, points_source, points_dest, number_of_points, manual_selection):

    if manual_selection == True:
        plt.imshow(image_source)
        selected_point_pairs_im_source = plt.ginput(number_of_points, timeout=3000, show_clicks=True)
        np.save(input_path_image_source, selected_point_pairs_im_source)
        plt.close()

        plt.imshow(image_dest)
        selected_point_pairs_im_dest = plt.ginput(number_of_points, timeout=3000, show_clicks=True)
        np.save(input_path_image_dest, selected_point_pairs_im_dest)
        plt.close()
    else:
        selected_point_pairs_im_source = np.load(points_source)
        selected_point_pairs_im_dest = np.load(points_dest)

    return selected_point_pairs_im_source, selected_point_pairs_im_dest


# 2. Homography estimation
def computeH(points_im1, points_im2):
    A = []
    number_of_points = len(points_im1)
    for i in range(number_of_points):
        x_1, y_1 = points_im1[i][0], points_im1[i][1] # x, y
        x_2, y_2 = points_im2[i][0], points_im2[i][1] # x' and y'
        A.append([x_1, y_1, 1, 0, 0, 0, -x_1*x_2, -y_1*x_2, -x_2])
        A.append([0, 0, 0, x_1, y_1, 1, -x_1*y_2, -y_1*y_2, -y_2])
    U, S, V = np.linalg.svd(np.asarray(A))
    H = V[-1, :]/V[-1, -1]
    homography = H.reshape(3, 3)
    print("Homography matrix is calculated.")
    print("Homography: ", "\n", homography)
    return homography


# Homogeneous coordinate calculation
def homogeneous_coordinate(coordinate):
    x = coordinate[0]/coordinate[2]
    y = coordinate[1]/coordinate[2]
    return x, y


# 3. Backward image warping
def warp(image, homography):
    print("Warping is started.")

    image_array = np.array(image)
    row_number, column_number = int(image_array.shape[0]), int(image_array.shape[1])

    up_left_cor_x, up_left_cor_y = homogeneous_coordinate(np.dot(homography, [[0],[0],[1]]))
    up_right_cor_x, up_right_cor_y = homogeneous_coordinate(np.dot(homography, [[column_number-1],[0],[1]]))
    low_left_cor_x, low_left_cor_y = homogeneous_coordinate(np.dot(homography, [[0],[row_number-1],[1]]))
    low_right_cor_x, low_right_cor_y = homogeneous_coordinate(np.dot(homography, [[column_number-1],[row_number-1],[1]]))

    x_values = [up_left_cor_x, up_right_cor_x, low_right_cor_x, low_left_cor_x]
    y_values = [up_left_cor_y, up_right_cor_y, low_left_cor_y,  low_right_cor_y]
    print("x_values: ", x_values, "\n y_values: ", y_values)

    offset_x = math.floor(min(x_values))
    offset_y = math.floor(min(y_values))
    print("offset_x: ", offset_x, "\t size_y: ", offset_x)

    max_x = math.ceil(max(x_values))
    max_y = math.ceil(max(y_values))

    size_x = max_x - offset_x
    size_y = max_y - offset_y
    print("size_x: ", size_x, "\t size_y: ", size_y)

    homography_inverse = np.linalg.inv(homography)
    print("Homography inverse: ", "\n", homography_inverse)

    result = np.zeros((size_y, size_x, 3))

    for x in range(size_x):
        for y in range(size_y):
            point_xy = homogeneous_coordinate(np.dot(homography_inverse, [[x+offset_x], [y+offset_y], [1]]))
            point_x = int(point_xy[0])
            point_y = int(point_xy[1])

            if (point_x >= 0 and point_x < column_number and point_y >= 0 and point_y < row_number):
                result[y, x, :] = image_array[point_y, point_x, :]

    print("Warping is completed.")
    return result, offset_x, offset_y


# 4. Image stitching using 2 images
def blending2images(base_array, image_array, offset_x, offset_y):
    print("Blending two images is started.")

    #image_array = np.array(image_array)
    #base_array = np.array(base_array)

    rows_base, columns_base = int(base_array.shape[0]), int(base_array.shape[1])
    rows_image, columns_image = int(image_array.shape[0]), int(image_array.shape[1])

    print("Column number of base: ", columns_base, "\t Row number of base: ", rows_base)
    print("Column number of image: ", columns_image, "\t Row number of image: ", rows_image)

    x_min = 0
    if offset_x>0:
        x_max = max([offset_x+columns_image, columns_base])
    else:
        x_max = max([-offset_x + columns_base, columns_image])

    y_min = 0
    # note that offset_y was always negative in this assignment.
    y_max = max([rows_base-offset_y, rows_image])

    size_x = x_max - x_min
    size_y = y_max - y_min

    print("size_x: ", size_x, "\t size_y: ", size_y)
    blending = np.zeros((size_y, size_x, 3))

    # right to left image stitching
    if offset_x > 0:
        blending[:rows_image, offset_x:columns_image+offset_x, :] = image_array[:, :, :]
        blending[-offset_y:rows_base-offset_y, :columns_base, :] = base_array[:, :, :]
    # left to right image stitching
    else:
        blending[:rows_image, :columns_image, :] = image_array[:, :, :]
        blending[-offset_y:rows_base-offset_y, -offset_x:columns_base-offset_x, :] = base_array[:, :, :]

    print("Blending is completed.")
    return blending


# 4. Image stitching using 3 images
def blend3images(left, middle, right, left_middle_offset_x, left_middle_offset_y, right_middle_offset_x, right_middle_offset_y):
    print("Blending three images is started.")

    #left = np.array(left)
    #middle = np.array(middle)
    #right = np.array(right)

    rows_left, columns_left = int(left.shape[0]), int(left.shape[1])
    rows_middle, columns_middle = int(middle.shape[0]), int(middle.shape[1])
    rows_right, columns_right = int(right.shape[0]), int(right.shape[1])

    print("Column number of left: ", columns_left, "\t Row number of base: ", rows_left)
    print("Column number of middle: ", columns_middle, "\t Row number of middle: ", rows_middle)
    print("Column number of right: ", columns_right, "\t Row number of right: ", rows_right)

    x_min = min([left_middle_offset_x, right_middle_offset_x, 0])
    x_max = max([left_middle_offset_x+columns_left, right_middle_offset_x+columns_right, columns_middle])

    y_min = min([left_middle_offset_y, right_middle_offset_y, 0])
    y_max = max([rows_left+left_middle_offset_y, rows_right+right_middle_offset_y, rows_middle])

    size_x = x_max - x_min
    size_y = y_max - y_min

    print("size_x: ", size_x, "\t size_y: ", size_y)
    blending = np.zeros((size_y, size_x, 3))

    #left
    blending[:rows_left, :columns_left, :] = left[:, :, :]

    #right
    blending[size_y-rows_right:, size_x-columns_right:, :] = right[:, :, :]
    blending[size_y - rows_right:, size_x - columns_right:, :] = np.where(
        blending[size_y - rows_right:, size_x - columns_right:, :] == [0, 0, 0],
        right[:, :, :], blending[size_y - rows_right:, size_x - columns_right:, :])

    #middle
    #blending[-left_middle_offset_y:rows_middle-left_middle_offset_y, -left_middle_offset_x:columns_middle-left_middle_offset_x, :] = middle[:, :, :]

    blending[-left_middle_offset_y:rows_middle-left_middle_offset_y, -left_middle_offset_x:columns_middle-left_middle_offset_x, :] = \
       np.where(np.mean(middle[:2], axis=0) <
                np.mean(blending[-left_middle_offset_y:rows_middle-left_middle_offset_y, -left_middle_offset_x:columns_middle-left_middle_offset_x, :][:2], axis=0),
                blending[-left_middle_offset_y:rows_middle-left_middle_offset_y, -left_middle_offset_x:columns_middle-left_middle_offset_x, :], middle)

    print("Blending is completed.")
    return blending


# Main function
def main():

    input_path_image_source1 = "images\paris_a.jpg"
    input_path_image_source2 = "images\paris_c.jpg"
    input_path_image_dest = "images\paris_b.jpg" # base
    image_source1 = Image.open(input_path_image_source1)
    image_source2 = Image.open(input_path_image_source2)
    image_dest = Image.open(input_path_image_dest)

    points_source1 = "points\points_paris_a_-paris_ab.npy"
    points_dest1 = "points\points_paris_b_-paris_ab.npy"
    points_source2 = "points\points_paris_c_-paris_bc.npy"
    points_dest2 = "points\points_paris_b_-paris_bc.npy"

    number_of_points = 10
    manual_selection = False

    # paris_a and paris_b
    selected_point_pairs_im_source1, selected_point_pairs_im_dest1 = selectingPoints(
        input_path_image_source1, input_path_image_dest, image_source1, image_dest,
        points_source1, points_dest1, number_of_points, manual_selection)

    homography1 = computeH(np.array(selected_point_pairs_im_source1), np.array(selected_point_pairs_im_dest1))

    warped_image_source1, source1_offset_x, source1_offset_y = warp(image_source1, homography1)

    image = Image.fromarray(warped_image_source1.astype('uint8'), 'RGB')
    image.save("warped_" + input_path_image_source1[-11:])

    # paris_b and paris_c
    selected_point_pairs_im_source2, selected_point_pairs_im_dest2 = selectingPoints(
        input_path_image_source2, input_path_image_dest, image_source2, image_dest,
        points_source2, points_dest2, number_of_points, manual_selection)
    homography2 = computeH(np.array(selected_point_pairs_im_source2), np.array(selected_point_pairs_im_dest2))
    warped_image_source2, source2_offset_x, source2_offset_y = warp(image_source2, homography2)
    image = Image.fromarray(warped_image_source2.astype('uint8'), 'RGB')
    image.save("warped_" + input_path_image_source2[-11:])

    # Stitching 3 images
    result_blended = blend3images(warped_image_source1, np.array(image_dest), warped_image_source2,
                                  source1_offset_x, source1_offset_y, source2_offset_x, source2_offset_y)

    # Stitching 2 images
    #result_blended = blend2images(warped_image_source1, np.array(image_dest), source1_offset_x, source1_offset_y)

    image = Image.fromarray(result_blended.astype('uint8'), 'RGB')
    image.save("blended_image.jpg")
    print("Blended image is generated.")

# Call main function
if __name__ == '__main__':
    main()