# coding: utf-8

from paintjob_designer.core import Container

container = Container()

container.register_lazy("config_path_resolver", "paintjob_designer.config.config_path_resolver:ConfigPathResolver")
container.register("config_path", lambda c: c.resolve("config_path_resolver").default_path())
container.register_lazy("config_store", "paintjob_designer.config.store:ConfigStore", "config_path")
container.register_lazy("iso_root_validator", "paintjob_designer.config.iso_root_validator:IsoRootValidator")
container.register_lazy("slugifier", "paintjob_designer.core:Slugifier")
container.register_lazy("app_icon", "paintjob_designer.gui.app_icon:AppIcon")

container.register_lazy("color_converter", "paintjob_designer.color.converter:ColorConverter")
container.register_lazy(
    "color_transformer", "paintjob_designer.color.transform:ColorTransformer",
    "color_converter",
)
container.register_lazy(
    "gradient_generator", "paintjob_designer.color.gradient:GradientGenerator",
    "color_converter",
)

container.register_lazy("profile_reader", "paintjob_designer.profile.reader:ProfileReader")
container.register_lazy("skin_slot_deriver", "paintjob_designer.profile.skin_slot_deriver:SkinSlotDeriver")
container.register_lazy("animation_decoder", "paintjob_designer.ctr.animation:AnimationDecoder")
container.register_lazy(
    "ctr_model_reader", "paintjob_designer.ctr.reader:CtrModelReader",
    "animation_decoder",
)
container.register_lazy(
    "profile_loader", "paintjob_designer.profile.loader:ProfileLoader",
    "profile_reader",
    "ctr_model_reader",
    "skin_slot_deriver",
)
container.register_lazy("profile_holder", "paintjob_designer.gui.controller.profile_holder:ProfileHolder")
container.register("profile_getter", lambda c: c.resolve("profile_holder").get)
container.register_lazy(
    "character_picker", "paintjob_designer.gui.controller.character_picker:CharacterPicker",
    "profile_getter",
)

container.register_lazy("vertex_assembler", "paintjob_designer.ctr.vertex_assembler:VertexAssembler")
container.register_lazy("slot_region_deriver", "paintjob_designer.render.slot_region_deriver:SlotRegionDeriver")
container.register_lazy("vram_reader", "paintjob_designer.vram.reader:VramReader")
container.register_lazy("vram_cache", "paintjob_designer.vram.cache:VramCache", "vram_reader")
container.register_lazy(
    "atlas_renderer", "paintjob_designer.render.atlas_renderer:AtlasRenderer",
    "color_converter",
)
container.register_lazy("atlas_uv_mapper", "paintjob_designer.render.atlas_uv_mapper:AtlasUvMapper")
container.register_lazy("ray_triangle_picker", "paintjob_designer.render.ray_picker:RayTrianglePicker")
container.register_lazy("blend_mode_grouper", "paintjob_designer.render.blend_mode_grouper:BlendModeGrouper")
container.register_lazy("wheel_geometry", "paintjob_designer.render.wheel_geometry:WheelGeometry")
container.register_lazy("preview_image_writer", "paintjob_designer.render.preview_image_writer:PreviewImageWriter")

container.register_lazy("paintjob_reader", "paintjob_designer.paintjob.reader:PaintjobReader")
container.register_lazy("paintjob_writer", "paintjob_designer.paintjob.writer:PaintjobWriter")
container.register_lazy("skin_reader", "paintjob_designer.skin.reader:SkinReader")
container.register_lazy("skin_writer", "paintjob_designer.skin.writer:SkinWriter")
container.register_lazy("wheel_reader", "paintjob_designer.wheel.reader:WheelReader")
container.register_lazy("wheel_writer", "paintjob_designer.wheel.writer:WheelWriter")

container.register_lazy("message_dialog", "paintjob_designer.gui.util.dialogs:MessageDialog")
container.register_lazy("file_picker", "paintjob_designer.gui.util.dialogs:FilePicker")
container.register_lazy("input_prompt", "paintjob_designer.gui.util.dialogs:InputPrompt")
container.register_lazy("library_writer", "paintjob_designer.gui.util.library_writer:LibraryWriter")
container.register_lazy(
    "psx_color_picker", "paintjob_designer.gui.widget.color_picker:PsxColorPicker",
    "color_converter",
)

container.register_lazy("four_bpp_codec", "paintjob_designer.texture.four_bpp_codec:FourBppCodec")
container.register_lazy(
    "texture_quantizer", "paintjob_designer.texture.texture_quantizer:TextureQuantizer",
    "color_converter",
)
container.register_lazy(
    "single_region_texture_importer",
    "paintjob_designer.texture.single_region_texture_importer:SingleRegionTextureImporter",
    "texture_quantizer",
)
container.register_lazy(
    "multi_region_texture_importer",
    "paintjob_designer.texture.multi_region_texture_importer:MultiRegionTextureImporter",
    "texture_quantizer",
    "four_bpp_codec",
)
container.register_lazy(
    "texture_rotator", "paintjob_designer.texture.texture_rotator:TextureRotator",
    "four_bpp_codec",
)
container.register_lazy(
    "texture_exporter", "paintjob_designer.texture.texture_exporter:TextureExporter",
    "color_converter",
    "four_bpp_codec",
)
container.register_lazy(
    "wheel_sheet", "paintjob_designer.texture.wheel_sheet:WheelSheet",
    "texture_quantizer",
    "texture_exporter",
)
container.register("wheel_sheet_provider", lambda c: c.provider("wheel_sheet"))
container.register_lazy(
    "palette_from_image_creator", "paintjob_designer.palette.palette_from_image_creator:PaletteFromImageCreator",
    "texture_quantizer",
)
container.register("palette_from_image_provider", lambda c: c.provider("palette_from_image_creator"))
container.register_lazy(
    "palette_from_colors_creator", "paintjob_designer.palette.palette_from_colors_creator:PaletteFromColorsCreator",
)

container.register_lazy(
    "character_handler", "paintjob_designer.gui.handler.character_handler:CharacterHandler",
    "ctr_model_reader",
    "vram_cache",
    "slot_region_deriver",
    "atlas_renderer",
    "wheel_geometry",
)
container.register_lazy(
    "color_handler", "paintjob_designer.gui.handler.color_handler:ColorHandler",
    "vram_cache",
    "atlas_renderer",
)
container.register_lazy(
    "project_handler", "paintjob_designer.gui.handler.project_handler:ProjectHandler",
    "paintjob_reader",
    "paintjob_writer",
)

container.register_lazy(
    "paintjob_library_sidebar", "paintjob_designer.gui.widget.paintjob_library_sidebar:PaintjobLibrarySidebar",
)
container.register_lazy(
    "skin_library_sidebar", "paintjob_designer.gui.widget.skin_library_sidebar:SkinLibrarySidebar",
)
container.register_lazy(
    "wheel_library_sidebar", "paintjob_designer.gui.widget.wheel_library_sidebar:WheelLibrarySidebar",
)
container.register_lazy(
    "palette_sidebar", "paintjob_designer.gui.widget.palette_sidebar:PaletteSidebar",
    "color_converter",
)
container.register_lazy(
    "paintjob_library_controller", "paintjob_designer.gui.controller.paintjob_library_controller:PaintjobLibraryController",
    "paintjob_library_sidebar",
    "project_handler",
    "paintjob_writer",
    "library_writer",
    "message_dialog",
    "file_picker",
    "input_prompt",
    "slugifier",
    "character_picker",
    "color_handler",
)
container.register_lazy(
    "skin_library_controller", "paintjob_designer.gui.controller.skin_library_controller:SkinLibraryController",
    "skin_library_sidebar",
    "skin_reader",
    "skin_writer",
    "library_writer",
    "message_dialog",
    "file_picker",
    "input_prompt",
    "slugifier",
    "character_picker",
    "color_handler",
)
container.register_lazy(
    "wheel_library_controller", "paintjob_designer.gui.controller.wheel_library_controller:WheelLibraryController",
    "wheel_library_sidebar",
    "wheel_reader",
    "wheel_writer",
    "library_writer",
    "wheel_sheet_provider",
    "message_dialog",
    "file_picker",
    "slugifier",
    "color_handler",
    "wheel_geometry",
)
container.register_lazy(
    "palette_library_controller", "paintjob_designer.gui.controller.palette_library_controller:PaletteLibraryController",
    "palette_sidebar",
    "color_converter",
    "message_dialog",
    "input_prompt",
    "file_picker",
    "palette_from_image_provider",
    "palette_from_colors_creator",
    "psx_color_picker",
)

container.register_lazy("preview_sidebar", "paintjob_designer.gui.widget.preview_sidebar:PreviewSidebar")
container.register_lazy(
    "slot_editor", "paintjob_designer.gui.widget.slot_editor:SlotEditor",
    "color_converter",
)
container.register_lazy(
    "orphan_slot_editor", "paintjob_designer.gui.widget.slot_editor:SlotEditor",
    "color_converter",
)
container.register_lazy("vertex_slot_editor", "paintjob_designer.gui.widget.vertex_slot_editor:VertexSlotEditor")
container.register_lazy(
    "kart_viewer", "paintjob_designer.gui.widget.kart_viewer:KartViewer",
    "atlas_uv_mapper",
    "ray_triangle_picker",
    "blend_mode_grouper",
    "wheel_geometry",
)
