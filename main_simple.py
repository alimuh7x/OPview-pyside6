#!/usr/bin/env python3
"""
VTK Previewer - Simple version without OpenGL issues
"""

import sys
import os
from pathlib import Path

# Set VTK to use OSMesa (off-screen rendering)
os.environ['VTK_DEFAULT_RENDER_WINDOW'] = 'vtkOSMesaRenderWindow'

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QLabel, QGroupBox, QGridLayout, QMessageBox, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage

import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkIOXML import vtkXMLImageDataReader, vtkXMLStructuredGridReader, vtkXMLUnstructuredGridReader
from vtkmodules.vtkIOLegacy import vtkDataSetReader
from vtkmodules.vtkRenderingCore import (
    vtkActor, vtkPolyDataMapper, vtkRenderer, vtkRenderWindow, vtkWindowToImageFilter
)
from vtkmodules.vtkRenderingAnnotation import vtkScalarBarActor
from vtkmodules.vtkFiltersCore import vtkContourFilter
from vtkmodules.vtkCommonDataModel import vtkImageData, vtkStructuredGrid
from vtkmodules.vtkFiltersGeometry import vtkDataSetSurfaceFilter


class VTKPreviewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.reader = None
        self.dataset = None
        self.actor = None
        self.scalar_bar = None
        self.zoom_factor = 1.0
        self.colorbar_x = 0.90
        self.colorbar_y = 0.25
        self.dragging_colorbar = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0

        self.setWindowTitle("VTK Previewer (Simple)")
        self.resize(1200, 800)

        self.setup_ui()
        self.setup_vtk()

    def setup_ui(self):
        """Setup the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        # Left panel for controls
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel, stretch=1)

        # Right panel for image display
        display_panel = self.create_display_panel()
        main_layout.addWidget(display_panel, stretch=3)

    def create_control_panel(self):
        """Create the control panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # File controls
        file_group = QGroupBox("File Controls")
        file_layout = QVBoxLayout()

        self.load_btn = QPushButton("Load VTK File")
        self.load_btn.clicked.connect(self.load_vtk_file)
        file_layout.addWidget(self.load_btn)

        self.file_label = QLabel("No file loaded")
        self.file_label.setWordWrap(True)
        file_layout.addWidget(self.file_label)

        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # Dataset info
        info_group = QGroupBox("Dataset Information")
        info_layout = QGridLayout()

        self.info_type = QLabel("-")
        self.info_points = QLabel("-")
        self.info_cells = QLabel("-")
        self.info_arrays = QLabel("-")

        info_layout.addWidget(QLabel("Type:"), 0, 0)
        info_layout.addWidget(self.info_type, 0, 1)
        info_layout.addWidget(QLabel("Points:"), 1, 0)
        info_layout.addWidget(self.info_points, 1, 1)
        info_layout.addWidget(QLabel("Cells:"), 2, 0)
        info_layout.addWidget(self.info_cells, 2, 1)
        info_layout.addWidget(QLabel("Arrays:"), 3, 0)
        info_layout.addWidget(self.info_arrays, 3, 1)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Array selection
        array_group = QGroupBox("Array Selection")
        array_layout = QVBoxLayout()

        array_layout.addWidget(QLabel("Select array to visualize:"))
        self.array_combo = QComboBox()
        self.array_combo.currentIndexChanged.connect(self.on_array_changed)
        self.array_combo.setEnabled(False)
        array_layout.addWidget(self.array_combo)

        array_group.setLayout(array_layout)
        layout.addWidget(array_group)

        # Zoom controls
        zoom_group = QGroupBox("Zoom Controls")
        zoom_layout = QVBoxLayout()

        self.zoom_label = QLabel("Zoom: 100%")
        self.zoom_label.setAlignment(Qt.AlignCenter)
        zoom_layout.addWidget(self.zoom_label)

        zoom_buttons_layout = QHBoxLayout()

        self.zoom_05_btn = QPushButton("0.5x")
        self.zoom_05_btn.clicked.connect(lambda: self.set_zoom(0.5))
        zoom_buttons_layout.addWidget(self.zoom_05_btn)

        self.zoom_1_btn = QPushButton("1x")
        self.zoom_1_btn.clicked.connect(lambda: self.set_zoom(1.0))
        zoom_buttons_layout.addWidget(self.zoom_1_btn)

        self.zoom_2_btn = QPushButton("2x")
        self.zoom_2_btn.clicked.connect(lambda: self.set_zoom(2.0))
        zoom_buttons_layout.addWidget(self.zoom_2_btn)

        zoom_layout.addLayout(zoom_buttons_layout)

        zoom_info = QLabel("Use mouse wheel to zoom")
        zoom_info.setStyleSheet("font-size: 10px; color: gray;")
        zoom_info.setAlignment(Qt.AlignCenter)
        zoom_layout.addWidget(zoom_info)

        zoom_group.setLayout(zoom_layout)
        layout.addWidget(zoom_group)

        # Color bar position controls
        colorbar_group = QGroupBox("Color Bar Position")
        colorbar_layout = QVBoxLayout()

        info_label = QLabel("Click & drag color bar\nor use preset positions:")
        info_label.setStyleSheet("font-size: 10px; color: gray;")
        info_label.setAlignment(Qt.AlignCenter)
        colorbar_layout.addWidget(info_label)

        colorbar_btn_layout = QGridLayout()

        # Position buttons
        self.cb_top_right = QPushButton("Top Right")
        self.cb_top_right.clicked.connect(lambda: self.set_colorbar_position(0.90, 0.65))
        colorbar_btn_layout.addWidget(self.cb_top_right, 0, 1)

        self.cb_bottom_right = QPushButton("Bottom Right")
        self.cb_bottom_right.clicked.connect(lambda: self.set_colorbar_position(0.90, 0.15))
        colorbar_btn_layout.addWidget(self.cb_bottom_right, 1, 1)

        self.cb_top_left = QPushButton("Top Left")
        self.cb_top_left.clicked.connect(lambda: self.set_colorbar_position(0.02, 0.65))
        colorbar_btn_layout.addWidget(self.cb_top_left, 0, 0)

        self.cb_bottom_left = QPushButton("Bottom Left")
        self.cb_bottom_left.clicked.connect(lambda: self.set_colorbar_position(0.02, 0.15))
        colorbar_btn_layout.addWidget(self.cb_bottom_left, 1, 0)

        colorbar_layout.addLayout(colorbar_btn_layout)

        colorbar_group.setLayout(colorbar_layout)
        layout.addWidget(colorbar_group)

        # Rendering controls
        render_group = QGroupBox("Rendering Controls")
        render_layout = QVBoxLayout()

        self.render_btn = QPushButton("Render View")
        self.render_btn.clicked.connect(self.render_view)
        self.render_btn.setEnabled(False)
        render_layout.addWidget(self.render_btn)

        self.clear_btn = QPushButton("Clear Scene")
        self.clear_btn.clicked.connect(self.clear_scene)
        render_layout.addWidget(self.clear_btn)

        render_group.setLayout(render_layout)
        layout.addWidget(render_group)

        layout.addStretch()

        return panel

    def create_display_panel(self):
        """Create the display panel for rendered images"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        self.image_label = QLabel("Load a VTK file to preview")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("QLabel { background-color: white; color: #333333; }")
        self.image_label.setMinimumSize(800, 600)
        self.image_label.setScaledContents(False)
        self.image_label.setMouseTracking(True)  # Enable mouse tracking

        # Enable mouse events
        self.image_label.wheelEvent = self.wheel_event
        self.image_label.mousePressEvent = self.mouse_press_event
        self.image_label.mouseMoveEvent = self.mouse_move_event
        self.image_label.mouseReleaseEvent = self.mouse_release_event

        layout.addWidget(self.image_label)

        return panel

    def setup_vtk(self):
        """Setup VTK renderer (offscreen)"""
        self.renderer = vtkRenderer()
        colors = vtkNamedColors()
        self.renderer.SetBackground(colors.GetColor3d("White"))

        self.render_window = vtkRenderWindow()
        self.render_window.SetOffScreenRendering(1)
        self.render_window.AddRenderer(self.renderer)
        self.render_window.SetSize(1200, 900)
        self.render_window.SetMultiSamples(8)

    def load_vtk_file(self):
        """Load a VTK file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open VTK File",
            str(Path.cwd()),
            "VTK Files (*.vti *.vts *.vtu *.vtk);;All Files (*)"
        )

        if not file_path:
            return

        self.current_file = file_path
        self.file_label.setText(f"File: {Path(file_path).name}")

        ext = Path(file_path).suffix.lower()

        try:
            if ext == '.vti':
                self.reader = vtkXMLImageDataReader()
            elif ext == '.vts':
                self.reader = vtkXMLStructuredGridReader()
            elif ext == '.vtu':
                self.reader = vtkXMLUnstructuredGridReader()
            elif ext == '.vtk':
                self.reader = vtkDataSetReader()
            else:
                QMessageBox.warning(self, "Error", f"Unsupported file type: {ext}")
                return

            self.reader.SetFileName(file_path)
            self.reader.Update()

            self.dataset = self.reader.GetOutput()
            self.update_info()
            self.visualize_dataset()
            self.render_btn.setEnabled(True)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading file: {str(e)}")

    def update_info(self):
        """Update dataset information"""
        if self.dataset is None:
            return

        dataset_type = self.dataset.GetClassName()
        num_points = self.dataset.GetNumberOfPoints()
        num_cells = self.dataset.GetNumberOfCells()

        point_data = self.dataset.GetPointData()
        num_arrays = point_data.GetNumberOfArrays()

        self.info_type.setText(dataset_type)
        self.info_points.setText(str(num_points))
        self.info_cells.setText(str(num_cells))
        self.info_arrays.setText(str(num_arrays))

        # Populate array combo box
        self.array_combo.clear()
        for i in range(num_arrays):
            array_name = point_data.GetArrayName(i)
            self.array_combo.addItem(array_name, i)

        if num_arrays > 0:
            self.array_combo.setEnabled(True)
        else:
            self.array_combo.setEnabled(False)

    def on_array_changed(self, index):
        """Called when user selects a different array"""
        if self.dataset is not None and index >= 0:
            print(f"Array selection changed to index {index}: {self.array_combo.currentText()}")
            self.visualize_dataset()

    def visualize_dataset(self):
        """Visualize the dataset"""
        if self.dataset is None:
            return

        try:
            # Clear previous actors
            if self.actor:
                self.renderer.RemoveActor(self.actor)

            # Create surface from dataset
            if isinstance(self.dataset, (vtkImageData, vtkStructuredGrid)):
                # For structured data, extract surface
                surface_filter = vtkDataSetSurfaceFilter()
                surface_filter.SetInputData(self.dataset)
                surface_filter.Update()

                output = surface_filter.GetOutput()
                print(f"Surface filter output: {output.GetNumberOfPoints()} points, {output.GetNumberOfCells()} cells")

                mapper = vtkPolyDataMapper()
                mapper.SetInputConnection(surface_filter.GetOutputPort())
                mapper.ScalarVisibilityOn()
            else:
                # For other types
                mapper = vtkPolyDataMapper()
                mapper.SetInputData(self.dataset)
                mapper.ScalarVisibilityOn()

            # Set up color mapping with lookup table
            from vtkmodules.vtkCommonCore import vtkLookupTable

            if self.dataset.GetPointData().GetNumberOfArrays() > 0:
                # Get selected array index from combo box
                array_index = self.array_combo.currentData()
                if array_index is None:
                    array_index = 0

                array = self.dataset.GetPointData().GetArray(array_index)
                if array:
                    array_name = array.GetName()
                    data_range = array.GetRange()

                    # Configure mapper to use point data and specific array
                    mapper.SetScalarModeToUsePointFieldData()
                    mapper.SelectColorArray(array_name)
                    mapper.SetScalarRange(data_range)

                    # Create a high-quality colorful lookup table
                    lut = vtkLookupTable()
                    lut.SetNumberOfColors(1024)  # More colors for smoother gradients
                    lut.SetHueRange(0.667, 0.0)  # Blue to red
                    lut.SetSaturationRange(1.0, 1.0)
                    lut.SetValueRange(1.0, 1.0)
                    lut.SetRange(data_range)
                    lut.SetRampToLinear()  # Smooth linear ramp
                    lut.Build()

                    mapper.SetLookupTable(lut)
                    mapper.SetScalarVisibility(True)
                    mapper.UseLookupTableScalarRangeOn()

                    print(f"Using array: {array_name} (index {array_index}), range: {data_range}")
                    print(f"Scalar visibility: {mapper.GetScalarVisibility()}")
                    print(f"Scalar mode: {mapper.GetScalarMode()}")

            # Create actor
            self.actor = vtkActor()
            self.actor.SetMapper(mapper)

            # Set rendering properties for colored surface
            self.actor.GetProperty().SetOpacity(1.0)
            self.actor.GetProperty().SetRepresentationToSurface()

            # Enable lighting for better 3D effect
            self.actor.GetProperty().SetAmbient(0.3)
            self.actor.GetProperty().SetDiffuse(0.6)
            self.actor.GetProperty().SetSpecular(0.3)

            # No edges - clean surface only
            self.actor.GetProperty().EdgeVisibilityOff()

            print(f"Actor representation set to surface with color mapping")

            # Check actor bounds
            bounds = self.actor.GetBounds()
            print(f"Actor bounds: {bounds}")

            # Remove old scalar bar if it exists
            if self.scalar_bar:
                self.renderer.RemoveViewProp(self.scalar_bar)

            # Create and add scalar bar
            if self.dataset.GetPointData().GetNumberOfArrays() > 0:
                self.scalar_bar = vtkScalarBarActor()
                self.scalar_bar.SetLookupTable(mapper.GetLookupTable())
                self.scalar_bar.SetTitle(mapper.GetArrayName())
                self.scalar_bar.SetNumberOfLabels(7)

                # Position and size
                self.scalar_bar.SetWidth(0.08)
                self.scalar_bar.SetHeight(0.5)
                self.scalar_bar.SetPosition(self.colorbar_x, self.colorbar_y)

                # Orientation - vertical
                self.scalar_bar.SetOrientationToVertical()

                # Style the scalar bar with larger fonts
                self.scalar_bar.GetTitleTextProperty().SetColor(0, 0, 0)
                self.scalar_bar.GetTitleTextProperty().SetFontSize(20)  # Larger title
                self.scalar_bar.GetTitleTextProperty().SetBold(True)
                self.scalar_bar.GetLabelTextProperty().SetColor(0, 0, 0)
                self.scalar_bar.GetLabelTextProperty().SetFontSize(18)  # Larger labels

                self.renderer.AddViewProp(self.scalar_bar)

            # Add to renderer
            self.renderer.AddActor(self.actor)
            self.renderer.ResetCamera()

            # Check if data is 2D (planar) and adjust camera and window size
            bounds = self.actor.GetBounds()
            x_range = bounds[1] - bounds[0]
            y_range = bounds[3] - bounds[2]
            z_range = bounds[5] - bounds[4]

            print(f"Data ranges - X: {x_range:.6f}, Y: {y_range:.6f}, Z: {z_range:.6f}")

            # Determine which dimension is smallest (the "flat" dimension)
            ranges = [x_range, y_range, z_range]
            min_range = min(ranges)
            max_range = max(ranges)

            # If one dimension is very small, it's 2D data
            if min_range < max_range * 0.1:
                camera = self.renderer.GetActiveCamera()
                center_x = (bounds[0] + bounds[1]) / 2
                center_y = (bounds[2] + bounds[3]) / 2
                center_z = (bounds[4] + bounds[5]) / 2
                distance = max_range * 2

                # Determine which plane the data is in and calculate aspect ratio
                if y_range == min_range:
                    # XZ plane (flat in Y direction)
                    print("Detected 2D data in XZ plane")
                    camera.SetPosition(center_x, center_y + distance, center_z)
                    camera.SetFocalPoint(center_x, center_y, center_z)
                    camera.SetViewUp(0, 0, 1)  # Z is up
                    aspect_ratio = x_range / z_range if z_range > 0 else 1.0
                elif z_range == min_range:
                    # XY plane (flat in Z direction)
                    print("Detected 2D data in XY plane")
                    camera.SetPosition(center_x, center_y, center_z + distance)
                    camera.SetFocalPoint(center_x, center_y, center_z)
                    camera.SetViewUp(0, 1, 0)  # Y is up
                    aspect_ratio = x_range / y_range if y_range > 0 else 1.0
                else:
                    # YZ plane (flat in X direction)
                    print("Detected 2D data in YZ plane")
                    camera.SetPosition(center_x + distance, center_y, center_z)
                    camera.SetFocalPoint(center_x, center_y, center_z)
                    camera.SetViewUp(0, 1, 0)  # Y is up
                    aspect_ratio = y_range / z_range if z_range > 0 else 1.0

                # Adjust render window size based on aspect ratio
                base_size = 1000
                if aspect_ratio > 1.0:
                    # Wider than tall
                    win_width = base_size
                    win_height = int(base_size / aspect_ratio)
                else:
                    # Taller than wide (or square)
                    win_width = int(base_size * aspect_ratio)
                    win_height = base_size

                print(f"Aspect ratio: {aspect_ratio:.2f}, Window size: {win_width}x{win_height}")
                self.render_window.SetSize(win_width, win_height)

                camera.ParallelProjectionOn()
                print(f"Camera position: {camera.GetPosition()}")
                print(f"Camera focal point: {camera.GetFocalPoint()}")
                self.renderer.ResetCamera()

            # Get camera position
            camera = self.renderer.GetActiveCamera()
            print(f"Camera position: {camera.GetPosition()}")
            print(f"Camera focal point: {camera.GetFocalPoint()}")

            print(f"Dataset visualized: {self.dataset.GetNumberOfPoints()} points, {self.dataset.GetNumberOfCells()} cells")
            print(f"Number of actors in renderer: {self.renderer.GetActors().GetNumberOfItems()}")

            # Render automatically
            self.render_view()

        except Exception as e:
            QMessageBox.critical(self, "Visualization Error", f"Error visualizing dataset: {str(e)}")
            print(f"Visualization error: {e}")

    def set_colorbar_position(self, x, y):
        """Set the color bar position"""
        if self.dataset is None or self.scalar_bar is None:
            return

        self.colorbar_x = x
        self.colorbar_y = y

        # Update scalar bar position
        self.scalar_bar.SetPosition(x, y)

        # Re-render
        self.render_view()

    def set_zoom(self, zoom_level):
        """Set the zoom level"""
        if self.dataset is None:
            return

        self.zoom_factor = zoom_level
        self.zoom_label.setText(f"Zoom: {int(zoom_level * 100)}%")

        # Apply zoom by adjusting camera's parallel scale
        camera = self.renderer.GetActiveCamera()
        if camera.GetParallelProjection():
            # Reset camera first to get default scale
            self.renderer.ResetCamera()
            # Then apply zoom by dividing parallel scale
            current_scale = camera.GetParallelScale()
            camera.SetParallelScale(current_scale / zoom_level)

        # Re-render
        self.render_view()

    def wheel_event(self, event):
        """Handle mouse wheel for zooming"""
        if self.dataset is None:
            return

        # Get wheel delta (positive = zoom in, negative = zoom out)
        delta = event.angleDelta().y()

        # Adjust zoom factor (0.1 per wheel step)
        zoom_change = 0.1 if delta > 0 else -0.1
        new_zoom = max(0.1, min(5.0, self.zoom_factor + zoom_change))

        self.set_zoom(new_zoom)

    def mouse_press_event(self, event):
        """Handle mouse press for color bar dragging"""
        if self.dataset is None or self.scalar_bar is None:
            return

        # Get click position in label coordinates
        click_x = int(event.position().x())
        click_y = int(event.position().y())

        # Get image dimensions and label size
        pixmap = self.image_label.pixmap()
        if pixmap is None:
            return

        img_width = pixmap.width()
        img_height = pixmap.height()
        label_width = self.image_label.width()
        label_height = self.image_label.height()

        # Calculate offset (image is centered in label)
        offset_x = (label_width - img_width) // 2
        offset_y = (label_height - img_height) // 2

        # Adjust click position to image coordinates
        img_click_x = click_x - offset_x
        img_click_y = click_y - offset_y

        # Check if click is within image bounds
        if img_click_x < 0 or img_click_x >= img_width or img_click_y < 0 or img_click_y >= img_height:
            print("Click outside image")
            return

        # Convert to normalized coordinates (0-1)
        norm_x = img_click_x / img_width
        norm_y = 1.0 - (img_click_y / img_height)  # Flip Y (Qt Y is top-down, VTK is bottom-up)

        print(f"Mouse press at pixel ({img_click_x}, {img_click_y}), normalized ({norm_x:.2f}, {norm_y:.2f})")
        print(f"Color bar at ({self.colorbar_x:.2f}, {self.colorbar_y:.2f})")

        # Check if click is near color bar (with some tolerance)
        cb_width = 0.08
        cb_height = 0.5
        tolerance = 0.1  # Increased tolerance

        # Color bar region: x from colorbar_x to colorbar_x + cb_width
        #                   y from colorbar_y to colorbar_y + cb_height
        if (norm_x >= self.colorbar_x - tolerance and
            norm_x <= self.colorbar_x + cb_width + tolerance and
            norm_y >= self.colorbar_y - tolerance and
            norm_y <= self.colorbar_y + cb_height + tolerance):
            # Click is on color bar
            print("Color bar clicked! Starting drag...")
            self.dragging_colorbar = True
            self.drag_offset_x = norm_x - self.colorbar_x
            self.drag_offset_y = norm_y - self.colorbar_y
            self.image_label.setCursor(Qt.CursorShape.ClosedHandCursor)
        else:
            print("Click outside color bar region")

    def mouse_move_event(self, event):
        """Handle mouse move for color bar dragging"""
        if not self.dragging_colorbar:
            return

        # Get current position in label coordinates
        move_x = int(event.position().x())
        move_y = int(event.position().y())

        # Get image dimensions and label size
        pixmap = self.image_label.pixmap()
        if pixmap is None:
            return

        img_width = pixmap.width()
        img_height = pixmap.height()
        label_width = self.image_label.width()
        label_height = self.image_label.height()

        # Calculate offset (image is centered in label)
        offset_x = (label_width - img_width) // 2
        offset_y = (label_height - img_height) // 2

        # Adjust to image coordinates
        img_move_x = move_x - offset_x
        img_move_y = move_y - offset_y

        # Convert to normalized coordinates
        norm_x = img_move_x / img_width
        norm_y = 1.0 - (img_move_y / img_height)

        # Calculate new color bar position (accounting for drag offset)
        new_x = norm_x - self.drag_offset_x
        new_y = norm_y - self.drag_offset_y

        # Clamp to valid range (keep color bar on screen)
        new_x = max(0.0, min(0.92, new_x))
        new_y = max(0.0, min(0.85, new_y))

        # Update position (don't render yet - wait for mouse release)
        self.colorbar_x = new_x
        self.colorbar_y = new_y

        if self.scalar_bar:
            self.scalar_bar.SetPosition(new_x, new_y)

    def mouse_release_event(self, event):
        """Handle mouse release to end color bar dragging"""
        if self.dragging_colorbar:
            self.dragging_colorbar = False
            self.image_label.setCursor(Qt.CursorShape.ArrowCursor)
            # Render once after drag is complete
            print(f"Drag complete, final position: ({self.colorbar_x:.2f}, {self.colorbar_y:.2f})")
            self.render_view()

    def render_view(self):
        """Render the current view to an image"""
        if self.actor is None:
            return

        try:
            # Render to window
            self.render_window.Render()
            print("Render window rendered")

            # Capture to image
            w2i = vtkWindowToImageFilter()
            w2i.SetInput(self.render_window)
            w2i.Update()

            vtk_image = w2i.GetOutput()
            width, height, _ = vtk_image.GetDimensions()
            print(f"Image dimensions: {width}x{height}")

            # Convert VTK image to QImage
            vtk_array = vtk_image.GetPointData().GetScalars()
            components = vtk_array.GetNumberOfComponents()
            print(f"Image components: {components}")

            # Create QImage
            from vtkmodules.util.numpy_support import vtk_to_numpy
            import numpy as np

            np_array = vtk_to_numpy(vtk_array)
            np_array = np_array.reshape(height, width, components)
            np_array = np.flip(np_array, axis=0)  # Flip vertically
            np_array = np.ascontiguousarray(np_array, dtype=np.uint8)  # Ensure contiguous

            if components == 3:
                qimage = QImage(np_array.data, width, height, width * components, QImage.Format_RGB888)
            else:
                qimage = QImage(np_array.data, width, height, width * components, QImage.Format_RGBA8888)

            # Display at original size - no scaling
            pixmap = QPixmap.fromImage(qimage.copy())
            self.image_label.setPixmap(pixmap)
            print("Image displayed successfully")

        except Exception as e:
            QMessageBox.critical(self, "Rendering Error", f"Error rendering view: {str(e)}")
            print(f"Rendering error: {e}")

    def clear_scene(self):
        """Clear the scene"""
        if self.actor:
            self.renderer.RemoveActor(self.actor)
            self.actor = None

        if self.scalar_bar:
            self.renderer.RemoveViewProp(self.scalar_bar)
            self.scalar_bar = None

        self.dataset = None
        self.reader = None
        self.current_file = None

        self.file_label.setText("No file loaded")
        self.info_type.setText("-")
        self.info_points.setText("-")
        self.info_cells.setText("-")
        self.info_arrays.setText("-")

        self.image_label.setText("Load a VTK file to preview")
        self.image_label.setPixmap(QPixmap())
        self.render_btn.setEnabled(False)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("VTK Previewer")

    window = VTKPreviewer()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
