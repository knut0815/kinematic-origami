import matplotlib
import matplotlib.pyplot as plt
from matplotlib import collections
from matplotlib.cm import ScalarMappable
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

def set_axes_equal(ax):
	'''Make axes of 3D plot have equal scale so that spheres appear as spheres,
	cubes as cubes, etc..  This is one possible solution to Matplotlib's
	ax.set_aspect('equal') and ax.axis('equal') not working for 3D.

	Input
	  ax: a matplotlib axis, e.g., as output from plt.gca().
	'''

	x_limits = ax.get_xlim3d()
	y_limits = ax.get_ylim3d()
	z_limits = ax.get_zlim3d()

	x_range = abs(x_limits[1] - x_limits[0])
	x_middle = np.mean(x_limits)
	y_range = abs(y_limits[1] - y_limits[0])
	y_middle = np.mean(y_limits)
	z_range = abs(z_limits[1] - z_limits[0])
	z_middle = np.mean(z_limits)

	# The plot bounding box is a sphere in the sense of the infinity
	# norm, hence I call half the max range the plot radius.
	plot_radius = 0.5*max([x_range, y_range, z_range])

	ax.set_xlim3d([x_middle - plot_radius, x_middle + plot_radius])
	ax.set_ylim3d([y_middle - plot_radius, y_middle + plot_radius])
	ax.set_zlim3d([z_middle - plot_radius, z_middle + plot_radius])

def plot_reference_configuration(axes_3d, crease_pattern):
	'''Draws the crease pattern in its intial (reference) configuration, where all fold
	angles are implicitly set to zero 

	'''
	fold_angles = np.array([0.0 for _ in range(crease_pattern.num_folds)])

	plot_custom_configuration(axes_3d, crease_pattern, fold_angles)

def plot_custom_configuration(axes_3d, crease_pattern, fold_angles, color_map_name='terrain', alpha=1.0, edges=False):
	'''Draws the crease pattern in a particular folded state

	'''
	# Matplotlib utility for mapping face indices to colors
	scalar_color_map = ScalarMappable(norm=matplotlib.cm.colors.Normalize(0, crease_pattern.num_faces), 
									  cmap=plt.get_cmap(color_map_name)) 

	# Grab the dimensions of the `Axes3D` object
	_, size_x = axes_3d.get_xlim3d()
	_, size_y = axes_3d.get_ylim3d()
	if len(fold_angles) != crease_pattern.num_folds:
		raise Error('Invalid number of fold angles')

	# Reset the collections object to effectively clear the screen
	axes_3d.collections = []

	# Compute the face map based on the provided fold angles
	face_map = crease_pattern.compute_folding_map(fold_angles)

	# Add all face polygons to one array (so that depth testing works)
	all_polys = []# np.zeros((crease_pattern.num_faces, np.max(crease_pattern.num_face_corner_points), 3))

	for i in range(crease_pattern.num_faces):
		# Grab all of the 2D corner points that form this face
		points_2d = crease_pattern.face_corner_points[i][:crease_pattern.num_face_corner_points[i]]
		extra_0 = np.zeros((np.shape(points_2d)[0], 1))
		extra_1 = np.ones((np.shape(points_2d)[0], 1))

		# "Expand" the 2D coordinates into 4D by adding zeros and ones
		points_3d = np.hstack((points_2d, extra_0))
		points_4d = np.hstack((points_3d, extra_1))

		# Grab the 4x4 transformation matrix
		composite = face_map[i]

		# Transform each corner point by the composite matrix
		for j in range(crease_pattern.num_face_corner_points[i]):
			points_4d[j] = np.dot(composite, points_4d[j])

		# Add a new polygon (drop the w-coordinate)
		fixed_face_center = np.append(crease_pattern.face_centers[crease_pattern.fixed_face], 0.0)
		all_polys.append(points_4d[:,:3] + [size_x * 0.5, size_y * 0.5, 0.0] - fixed_face_center)

	# Construct the actual polygon collection object and configure its draw state
	poly_collection = Poly3DCollection(all_polys)
	poly_collection.set_facecolor([scalar_color_map.to_rgba(i)[:3] for i in range(crease_pattern.num_faces)])
	poly_collection.set_alpha(alpha)
	poly_collection.set_zsort('max')
	
	if edges:
		poly_collection.set_edgecolor('k')

	axes_3d.add_collection3d(poly_collection)

def plot_crease_pattern(axes_2d, crease_pattern, color_map_name=None, annotate_folds=True, annotate_reference_points=True, annotate_faces=True):
	'''Draws the planar graph corresponding to this crease pattern, along with some
	helpful annotations

	'''
	if color_map_name:
		# Matplotlib utility for mapping fold indices to colors
		scalar_color_map = ScalarMappable(norm=matplotlib.cm.colors.Normalize(0, crease_pattern.num_folds), 
										  cmap=plt.get_cmap(color_map_name)) 

		colors = [scalar_color_map.to_rgba(i)[:3] for i in range(crease_pattern.num_folds)]
	else:
		# No color map was supplied - provide default colors based on crease
		# assignments:
		#
		# 		V folds (- target angle) -> blue
		# 		M folds (+ target angle) -> red
		m_color = (1, 0, 0)
		v_color = (0, 0, 1)
		b_color = (0, 0, 0)

		colors = []
		for i in range(crease_pattern.num_folds):
			if crease_pattern.fold_angle_target[i] < 0.0:
				colors.append(v_color)
			elif crease_pattern.fold_angle_target[i] > 0.0:
				colors.append(m_color)
			else:
				colors.append(b_color)

	line_segments = [[a, b] for a, b in zip(crease_pattern.p1, crease_pattern.p2)]
	line_segment_midpoints = [(a + b) * 0.5 for a, b in zip(crease_pattern.p1, crease_pattern.p2) ]
	line_collection = collections.LineCollection(line_segments, colors=colors, linewidths=1)
	
	axes_2d.add_collection(line_collection)
	axes_2d.scatter(crease_pattern.reference_points[:, 0], crease_pattern.reference_points[:, 1], zorder=2)

	aspect_ratio = 1.0
	xleft, xright = axes_2d.get_xlim()
	ybottom, ytop = axes_2d.get_ylim()
	axes_2d.set_aspect(abs((xright - xleft) / (ybottom - ytop)) * aspect_ratio)

	if annotate_folds:
		for i, (x, y) in enumerate(line_segment_midpoints):
			label = 'e{}\n{}-{}'.format(i, crease_pattern.fold_vector_points[i][0], crease_pattern.fold_vector_points[i][1])
			axes_2d.annotate(label, (x, y), textcoords="offset points", xytext=(0, 0), ha='center', fontsize=8, fontweight='bold')
	if annotate_reference_points:
		for i, (x, y) in enumerate(crease_pattern.reference_points):
			label = 'v{}'.format(i)
			axes_2d.annotate(label, (x, y), textcoords="offset points", xytext=(0, 4), ha='center', fontsize=8)
	if annotate_faces:
		for i, (x, y) in enumerate(crease_pattern.face_centers):
			label = 'F{}'.format(i)
			axes_2d.annotate(label, (x, y), textcoords="offset points", xytext=(0, 0), ha='center', fontsize=8)