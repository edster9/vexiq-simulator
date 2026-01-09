"""
LDraw Model Renderer for Ursina/Panda3D
=======================================

Reusable module for rendering LDraw MPD/LDR models in any Ursina application.
Handles coordinate transforms, color application, and shader-based lighting.

Usage:
    from ldraw_renderer import LDrawModelRenderer, render_ldraw_model

    # Simple usage - just render a model file
    entities = render_ldraw_model('models/ClawbotIQ.mpd')

    # Advanced usage - more control
    from ldraw_parser import parse_mpd
    doc = parse_mpd('models/ClawbotIQ.mpd')
    renderer = LDrawModelRenderer(doc)
    renderer.render()
    print(f"Loaded {renderer.part_count} parts")
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Import LDraw parser (doesn't depend on Ursina)
from ldraw_parser import parse_mpd, LDrawDocument, LDRAW_COLORS

# =============================================================================
# Scale Constants
# =============================================================================
MODEL_SCALE = 1.0      # Don't scale GLB models - they're exported at correct scale
POSITION_SCALE = 0.02  # Scale LDU positions to match GLB scale (GLB is 0.02x LDU)

# Default path for GLB models (relative to project root)
GLB_PATH = 'models/parts'  # GLB parts with vertex colors baked in

# =============================================================================
# Shader (created lazily to avoid importing Ursina at module load)
# =============================================================================
_normal_lighting_shader = None

def get_normal_lighting_shader():
    """Get the lighting shader (created on first use).

    Features:
    - Headlight diffuse lighting (light from camera)
    - Specular highlights for plastic/shiny look
    - Fresnel rim lighting
    - Color masking (white = colorable, non-white = baked)
    """
    global _normal_lighting_shader
    if _normal_lighting_shader is None:
        from ursina import Shader
        _normal_lighting_shader = Shader(
            vertex='''
#version 140

uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelViewMatrix;

in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;
in vec3 p3d_Normal;
in vec4 p3d_Color;

out vec2 texcoord;
out vec3 view_normal;
out vec3 view_pos;
out vec4 vertex_color;

void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    texcoord = p3d_MultiTexCoord0;
    view_normal = normalize(mat3(p3d_ModelViewMatrix) * p3d_Normal);
    view_pos = (p3d_ModelViewMatrix * p3d_Vertex).xyz;
    vertex_color = p3d_Color;
}
''',
            fragment='''
#version 140

uniform sampler2D p3d_Texture0;
uniform vec4 p3d_ColorScale;  // entity.color

in vec2 texcoord;
in vec3 view_normal;
in vec3 view_pos;
in vec4 vertex_color;

out vec4 fragColor;

void main() {
    vec3 n = normalize(view_normal);
    vec3 v = normalize(-view_pos);  // View direction (camera at origin in view space)

    // Light direction: headlight from camera
    vec3 l = vec3(0.0, 0.0, 1.0);

    // Diffuse lighting
    float diffuse = max(dot(n, l), 0.0);
    float ambient = 0.35;
    float diffuse_intensity = ambient + (1.0 - ambient) * diffuse;

    // Specular highlight (Blinn-Phong) for plastic shine
    vec3 h = normalize(l + v);  // Half vector
    float spec_angle = max(dot(n, h), 0.0);
    float shininess = 32.0;  // Higher = tighter highlight
    float specular = pow(spec_angle, shininess);

    // Fresnel effect - edges reflect more (plastic look)
    float fresnel = pow(1.0 - max(dot(n, v), 0.0), 3.0);
    float rim = fresnel * 0.15;  // Subtle rim lighting

    // Check if vertex color is white (colorable) or has baked-in color
    float is_white = step(0.95, vertex_color.r) * step(0.95, vertex_color.g) * step(0.95, vertex_color.b);

    // Mix: white areas get entity color, non-white areas keep baked color
    vec3 base_color = mix(vertex_color.rgb, p3d_ColorScale.rgb, is_white);

    // Combine: diffuse color + white specular highlight + rim
    vec3 final_color = base_color * diffuse_intensity;
    final_color += vec3(1.0) * specular * 0.25;  // White specular, 25% intensity
    final_color += vec3(1.0) * rim;  // White rim light

    // Clamp to prevent over-bright
    final_color = min(final_color, vec3(1.0));

    fragColor = vec4(final_color, 1.0);
}
'''
        )
    return _normal_lighting_shader


# =============================================================================
# LDraw Model Renderer Class
# =============================================================================

class LDrawModelRenderer:
    """
    Renders LDraw MPD/LDR models in Ursina.

    Handles:
    - Hierarchical submodel transforms
    - Coordinate system conversion (LDraw Y-down → Ursina Y-up)
    - Color inheritance (color 16)
    - Custom shader for proper lighting

    Args:
        doc: Parsed LDrawDocument from ldraw_parser
        glb_path: Path to GLB models (relative to project_root)
        project_root: Project root directory (for resolving model paths)
        parent: Optional parent Entity for all rendered parts
        use_shader: Whether to apply the normal lighting shader (default True)
        verbose: Print debug info during rendering (default False)
    """

    IDENTITY_MATRIX = (1, 0, 0, 0, 1, 0, 0, 0, 1)

    def __init__(self, doc: LDrawDocument,
                 glb_path: str = GLB_PATH,
                 project_root: Path = None,
                 parent = None,
                 use_shader: bool = True,
                 skip_rotation: bool = False,
                 y_offset: float = 0.0,
                 verbose: bool = False):
        self.doc = doc
        self.glb_path = glb_path
        self.parent = parent
        self.use_shader = use_shader
        self.skip_rotation = skip_rotation
        self.y_offset = y_offset  # Applied to all parts during rendering
        self.verbose = verbose

        # Use provided project_root or current working directory
        if project_root is None:
            self.project_root = Path.cwd()
        else:
            self.project_root = Path(project_root)

        # Tracking
        self.entities: List = []
        self.entities_by_submodel: Dict[str, List] = {}  # Entities grouped by submodel name
        self.part_count = 0
        self.triangle_count = 0
        self.missing_parts = set()

    def render(self, model_name: str = None) -> List:
        """
        Render the model and return list of created entities.

        Args:
            model_name: Which model to render (default: main model)

        Returns:
            List of Ursina Entity objects created
        """
        if model_name is None:
            model_name = self.doc.main_model

        if not model_name:
            print("Warning: No model to render")
            return []

        self._render_model(model_name)

        if self.verbose:
            print(f"\nRendered {self.part_count} parts")
            if self.missing_parts:
                print(f"Missing parts: {len(self.missing_parts)}")
                for p in sorted(self.missing_parts):
                    print(f"  - {p}")

        return self.entities

    def _render_model(self, model_name: str, parent_color: int = 72,
                      offset: tuple = (0, 0, 0), parent_rotation: tuple = None,
                      current_submodel: str = None):
        """Recursively render a model and its submodels.

        Args:
            model_name: Name of the model to render
            parent_color: Inherited color code (default 72 = VEX light gray)
            offset: Position offset from parent (LDU)
            parent_rotation: Rotation matrix from parent
            current_submodel: Top-level submodel name for entity grouping
        """
        if parent_rotation is None:
            parent_rotation = self.IDENTITY_MATRIX

        if model_name not in self.doc.models:
            if self.verbose:
                print(f"Warning: Model '{model_name}' not found")
            return

        model = self.doc.models[model_name]

        # Track which submodel we're in (for entity grouping)
        # If current_submodel is None, this model IS the top-level submodel
        submodel_for_parts = current_submodel if current_submodel else model_name

        if self.verbose:
            print(f"\nRendering model: {model_name} (submodel: {submodel_for_parts})")
            print(f"  Parts: {len(model.parts)}")

        for part in model.parts:
            self._render_part(part, parent_color, offset, parent_rotation, submodel_for_parts)

        for submodel_name, placement in model.submodel_refs:
            composed_rotation = self._matrix_multiply(
                parent_rotation, placement.rotation_matrix
            )
            local_pos = (placement.x, placement.y, placement.z)
            rotated_pos = self._transform_point(parent_rotation, local_pos)
            sub_offset = (
                offset[0] + rotated_pos[0],
                offset[1] + rotated_pos[1],
                offset[2] + rotated_pos[2],
            )
            sub_color = placement.color if placement.color != 16 else parent_color
            # Pass submodel_name as the new current_submodel (so parts are grouped by their top-level submodel)
            self._render_model(submodel_name, sub_color, sub_offset, composed_rotation, submodel_name)

    def _render_part(self, part, parent_color: int,
                     offset: tuple, parent_rotation: tuple,
                     submodel_name: str = None):
        """Render a single part as an Ursina entity.

        Args:
            part: The part to render
            parent_color: Inherited color code
            offset: Position offset from parent (LDU)
            parent_rotation: Rotation matrix from parent
            submodel_name: Name of the submodel this part belongs to (for grouping)
        """
        from ursina import Entity, color

        glb_name = part.glb_name

        # Build absolute path for existence check
        glb_absolute = self.project_root / self.glb_path / glb_name

        if not glb_absolute.exists():
            if glb_name not in self.missing_parts:
                self.missing_parts.add(glb_name)
                if self.verbose:
                    print(f"  Warning: Missing part: {glb_name}")
                    print(f"    Checked: {glb_absolute}")
            return

        # Use relative path with forward slashes for Panda3D compatibility
        glb_path_for_load = f"{self.glb_path}/{glb_name}"

        if self.verbose:
            print(f"    Loading: {glb_path_for_load}")

        # Transform part's local position by parent rotation
        local_pos = (part.x, part.y, part.z)
        rotated_pos = self._transform_point(parent_rotation, local_pos)

        # Compose rotation
        world_rotation = self._matrix_multiply(parent_rotation, part.rotation_matrix)

        # Calculate world position in LDU
        world_x_ldu = offset[0] + rotated_pos[0]
        world_y_ldu = offset[1] + rotated_pos[1]
        world_z_ldu = offset[2] + rotated_pos[2]

        # Convert to Ursina coordinates
        # LDraw: X=right, Y=down, Z=toward viewer
        # Ursina: X=right, Y=up, Z=forward
        # Only negate Y (the down->up flip)
        pos_x = world_x_ldu * POSITION_SCALE
        pos_y = -world_y_ldu * POSITION_SCALE + self.y_offset  # Negate Y + offset
        pos_z = world_z_ldu * POSITION_SCALE   # Z stays same
        
        # Get color
        color_code = part.color if part.color != 16 else parent_color
        r, g, b = self._get_color_rgb(color_code)

        try:
            from panda3d.core import LMatrix4f

            # Create entity with model path
            entity = Entity(
                model=glb_path_for_load,
                position=(pos_x, pos_y, pos_z),
                scale=MODEL_SCALE,
            )

            # Set parent if specified
            if self.parent is not None:
                entity.parent = self.parent

            # Apply shader for lighting, then set color
            if self.use_shader:
                entity.shader = get_normal_lighting_shader()
            entity.color = color.rgba(r, g, b, 1)

            # Apply rotation matrix (skip if skip_rotation flag)
            if not self.skip_rotation:
                a, b_, c, d, e, f, g_, h, i = world_rotation

                # Coordinate transform: C * M * C where C = diag(1, -1, 1)
                # This transforms the rotation for LDraw->Ursina Y-flip only
                a2, b2, c2 = a, -b_, c
                d2, e2, f2 = -d, e, -f
                g2, h2, i2 = g_, -h, i

                # Create Panda3D rotation matrix (column-major, so transposed)
                mat = LMatrix4f(
                    a2, d2, g2, 0,
                    b2, e2, h2, 0,
                    c2, f2, i2, 0,
                    0, 0, 0, 1
                )

                # Apply rotation, then re-apply position and scale (setMat overwrites them)
                entity.setMat(mat)
                entity.position = (pos_x, pos_y, pos_z)
                entity.scale = MODEL_SCALE

            # Store part number for filtering (e.g., wheel animation)
            entity.part_number = part.part_name.replace('.dat', '').replace('.DAT', '')

            # Store original rotation matrix for animation (we'll need this to add rotation)
            entity.ldraw_rotation = world_rotation

            self.entities.append(entity)
            self.part_count += 1
            self.triangle_count += self._count_triangles(entity)

            # Track entity by submodel name for animation
            if submodel_name:
                if submodel_name not in self.entities_by_submodel:
                    self.entities_by_submodel[submodel_name] = []
                self.entities_by_submodel[submodel_name].append(entity)

            if self.verbose:
                print(f"  Part {self.part_count}: {glb_name} (submodel: {submodel_name})")
                print(f"    Position: ({pos_x:.2f}, {pos_y:.2f}, {pos_z:.2f})")
                print(f"    Color: ({r:.2f}, {g:.2f}, {b:.2f})")
                print(f"    Visible: {entity.visible}, Enabled: {entity.enabled}")
                # Print rotation matrix for comparison with C++
                if not self.skip_rotation and self.part_count <= 5:
                    print(f"    LDraw rotation (row-major):")
                    a, b_, c, d, e, f, g_, h, i = world_rotation
                    print(f"      [{a:.2f}, {b_:.2f}, {c:.2f}]")
                    print(f"      [{d:.2f}, {e:.2f}, {f:.2f}]")
                    print(f"      [{g_:.2f}, {h:.2f}, {i:.2f}]")
                    a2, b2, c2 = a, -b_, c
                    d2, e2, f2 = -d, e, -f
                    g2, h2, i2 = g_, -h, i
                    print(f"    After C*M*C transform:")
                    print(f"      [{a2:.2f}, {b2:.2f}, {c2:.2f}]")
                    print(f"      [{d2:.2f}, {e2:.2f}, {f2:.2f}]")
                    print(f"      [{g2:.2f}, {h2:.2f}, {i2:.2f}]")

        except Exception as ex:
            if self.verbose:
                print(f"Error loading part {glb_name}: {ex}")
                import traceback
                traceback.print_exc()

    def _get_color_rgb(self, color_code: int) -> Tuple[float, float, float]:
        """Get RGB color (0-1 range) from LDraw color code."""
        if color_code in LDRAW_COLORS:
            r, g, b, _ = LDRAW_COLORS[color_code]
            return (r, g, b)
        return (0.5, 0.5, 0.5)

    def _matrix_multiply(self, m1: tuple, m2: tuple) -> tuple:
        """Multiply two 3x3 rotation matrices (row-major order)."""
        a1, b1, c1, d1, e1, f1, g1, h1, i1 = m1
        a2, b2, c2, d2, e2, f2, g2, h2, i2 = m2
        return (
            a1*a2 + b1*d2 + c1*g2, a1*b2 + b1*e2 + c1*h2, a1*c2 + b1*f2 + c1*i2,
            d1*a2 + e1*d2 + f1*g2, d1*b2 + e1*e2 + f1*h2, d1*c2 + e1*f2 + f1*i2,
            g1*a2 + h1*d2 + i1*g2, g1*b2 + h1*e2 + i1*h2, g1*c2 + h1*f2 + i1*i2,
        )

    def _transform_point(self, matrix: tuple, point: tuple) -> tuple:
        """Transform a 3D point by a 3x3 rotation matrix."""
        a, b, c, d, e, f, g, h, i = matrix
        x, y, z = point
        return (a*x + b*y + c*z, d*x + e*y + f*z, g*x + h*y + i*z)

    def _count_triangles(self, entity) -> int:
        """Count triangles in an entity's model."""
        try:
            if hasattr(entity, 'model') and entity.model:
                # For Ursina entities, model might be a NodePath
                model = entity.model
                if hasattr(model, 'findAllMatches'):
                    total = 0
                    for node in model.findAllMatches('**/+GeomNode'):
                        geom_node = node.node()
                        for i in range(geom_node.getNumGeoms()):
                            geom = geom_node.getGeom(i)
                            for j in range(geom.getNumPrimitives()):
                                prim = geom.getPrimitive(j)
                                total += prim.getNumFaces()
                    return total
        except:
            pass
        return 0


# =============================================================================
# Convenience Functions
# =============================================================================

def render_ldraw_model(model_path: str,
                       parent = None,
                       glb_path: str = GLB_PATH,
                       project_root: Path = None,
                       use_shader: bool = True,
                       verbose: bool = False) -> List:
    """
    Convenience function to render an LDraw model file.

    Args:
        model_path: Path to .mpd or .ldr file
        parent: Optional parent Entity for all parts
        glb_path: Path to GLB models folder (relative to project_root)
        project_root: Project root directory
        use_shader: Whether to apply lighting shader
        verbose: Print debug info

    Returns:
        List of created Entity objects
    """
    if project_root is None:
        project_root = Path.cwd()

    path = Path(model_path)
    if not path.is_absolute():
        path = project_root / path

    if not path.exists():
        print(f"Error: Model not found: {path}")
        return []

    doc = parse_mpd(str(path))
    renderer = LDrawModelRenderer(
        doc,
        glb_path=glb_path,
        project_root=project_root,
        parent=parent,
        use_shader=use_shader,
        verbose=verbose
    )
    return renderer.render()


def get_renderer_stats(renderer: LDrawModelRenderer) -> dict:
    """Get statistics from a renderer."""
    return {
        'part_count': renderer.part_count,
        'triangle_count': renderer.triangle_count,
        'missing_parts': list(renderer.missing_parts),
        'entity_count': len(renderer.entities),
    }
