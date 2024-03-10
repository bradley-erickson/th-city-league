red = '#e74c3c'
white = '#ffffff'
blue = '#3498db'
green = '#18bc9c'
primary = '#2c3e50'


def hex_to_rgb(hex):
    """ Convert a hex value to list of rgb triplets """
    return [int(hex[i:i+2], 16) for i in range(1, 6, 2)]


def rgb_to_hex(rgb):
    """ Convert a list of rgb triplets to a hex list """
    RGB = [int(x) for x in rgb]
    return '#' + ''.join(['0{0:x}'.format(v) if v < 16 else '{0:x}'.format(v) for v in RGB])


def linear_gradient(start_hex, finish_hex, n=50):
    """ Create a gradient of n values between 2 initial hex values """
    s = hex_to_rgb(start_hex)
    f = hex_to_rgb(finish_hex)

    rgb_list = [start_hex]
    for t in range(1, n):
        curr_vector = [
            int(s[j] + (float(t)/(n-1))*(f[j]-s[j]))
            for j in range(3)
        ]
        rgb_list.append(rgb_to_hex(curr_vector))

    return rgb_list


def transparent_gradient(hex_color, n=50):
    # Convert hex to RGB
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    # Create gradient
    gradient = []
    for i in range(n):
        alpha = i / (n - 1)
        rgba = (r, g, b, alpha)
        gradient.append(f"rgba({rgba[0]}, {rgba[1]}, {rgba[2]}, {rgba[3]:.2f})")

    return gradient


def create_color_map(color_list):
    """ Create the color map for graph objects """
    total_colors = len(color_list)
    colormap = [[0, color_list[0]]]
    for i, item in enumerate(color_list):
        ratio = i / total_colors
        colormap.append([ratio, item])
    colormap.append([1, color_list[-1]])
    return colormap


red_to_white = linear_gradient(red, white)
white_to_blue = linear_gradient(white, blue)
red_to_white_to_blue = red_to_white + white_to_blue

win_rate_color_bar = create_color_map(red_to_white_to_blue)

inclusion_bar = transparent_gradient(primary, 101)
green_gradient = transparent_gradient(green, 101)
red_gradient = transparent_gradient(red, 101)
blue_gradient = transparent_gradient(blue, 101)
