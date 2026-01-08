"""
Custom shader: View-space lighting + vertex colors.
Light comes from camera direction (headlight style) - consistent from any angle.
"""

from ursina import Shader

normal_lighting_shader = Shader(
    vertex='''
#version 140

uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelViewMatrix;

in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;
in vec3 p3d_Normal;
in vec4 p3d_Color;  // Vertex color

out vec2 texcoord;
out vec3 view_normal;
out vec4 vertex_color;

void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    texcoord = p3d_MultiTexCoord0;
    // Transform normal to view space (camera-relative)
    view_normal = normalize(mat3(p3d_ModelViewMatrix) * p3d_Normal);
    vertex_color = p3d_Color;
}
''',
    fragment='''
#version 140

uniform sampler2D p3d_Texture0;
uniform vec4 p3d_ColorScale;  // entity.color

in vec2 texcoord;
in vec3 view_normal;
in vec4 vertex_color;

out vec4 fragColor;

void main() {
    vec4 tex_color = texture(p3d_Texture0, texcoord);

    vec3 n = normalize(view_normal);

    // Headlight: light from camera (0,0,1 in view space)
    // Faces pointing at camera = bright, away = darker
    float facing = n.z;  // How much face points toward camera

    // Map to brightness: facing camera = 0.95, perpendicular = 0.825, away = 0.7
    float brightness = 0.7 + 0.25 * max(facing, 0.0);

    // Simple multiply: vertex_color is a MASK
    // White (1,1,1) = full entity color from MPD
    // Black (0,0,0) = stays black (rubber)
    vec4 base_color = p3d_ColorScale * vertex_color * tex_color;

    fragColor = vec4(base_color.rgb * brightness, base_color.a);
}
'''
)
