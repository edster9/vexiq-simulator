"""
Custom shader: View-space lighting + vertex colors with plastic material look.
Light comes from camera direction (headlight style) - consistent from any angle.

Features:
- Headlight diffuse lighting (light from camera)
- Specular highlights for plastic/shiny look
- Fresnel rim lighting
- Color masking (white = colorable, non-white = baked)

Color logic:
- White vertex color (1,1,1) = colorable area, uses entity.color from MPD
- Any other vertex color = preserved as-is (buttons, labels, rubber, etc.)
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
uniform vec4 p3d_ColorScale;  // entity.color from MPD

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
