<?php
/**
 * Plugin Name:       Boulder Budget Widget
 * Plugin URI:        https://github.com/brianckeegan/charting-boulder
 * Description:       Embeds the "Balance Boulder's Budget" interactive via a [boulder_budget] shortcode and a Gutenberg block. The widget is a self-contained React app; it is rendered inside an isolated, auto-resizing same-origin iframe so its styles never collide with the theme.
 * Version:           1.0.0
 * Requires at least: 6.1
 * Requires PHP:      7.4
 * Author:            Charting Boulder / Boulder Reporting Lab
 * License:           MIT
 * Text Domain:       boulder-budget-widget
 *
 * @package BoulderBudgetWidget
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // No direct access.
}

define( 'BBW_VERSION', '1.0.0' );
define( 'BBW_PLUGIN_DIR', plugin_dir_path( __FILE__ ) );
define( 'BBW_PLUGIN_URL', plugin_dir_url( __FILE__ ) );
define( 'BBW_WIDGET_REL', 'assets/boulder-budget-widget.html' ); // The compiled production build.

/**
 * Register the front-end assets (the small auto-resize script + wrapper CSS).
 * Registered here, enqueued on demand only where the shortcode/block renders.
 */
function bbw_register_assets() {
	wp_register_style(
		'boulder-budget-widget',
		BBW_PLUGIN_URL . 'assets/embed.css',
		array(),
		BBW_VERSION
	);
	wp_register_script(
		'boulder-budget-widget',
		BBW_PLUGIN_URL . 'assets/embed.js',
		array(),
		BBW_VERSION,
		true
	);
}
add_action( 'wp_enqueue_scripts', 'bbw_register_assets' );

/**
 * Resolve the URL + cache-busting version for the bundled widget HTML.
 *
 * @return array{0:string,1:string} [ url, version ] or [ '', '' ] if the file is missing.
 */
function bbw_widget_source() {
	$path = BBW_PLUGIN_DIR . BBW_WIDGET_REL;
	if ( ! file_exists( $path ) ) {
		return array( '', '' );
	}
	// filemtime busts the browser cache automatically whenever the bundle is replaced.
	return array( BBW_PLUGIN_URL . BBW_WIDGET_REL, (string) filemtime( $path ) );
}

/**
 * Sanitize a CSS length token (e.g. "720px", "80vh", "100%", "none").
 *
 * @param string $value Raw value.
 * @param string $fallback Fallback when empty/invalid.
 * @return string
 */
function bbw_css_len( $value, $fallback ) {
	$value = strtolower( trim( (string) $value ) );
	if ( '' === $value ) {
		return $fallback;
	}
	$value = preg_replace( '/[^0-9a-z%.]/', '', $value );
	return '' === $value ? $fallback : $value;
}

/**
 * Render the embed markup shared by the shortcode and the block.
 *
 * @param array $atts {
 *     @type string $src        Override the widget URL. Defaults to the bundled build.
 *                              Same-origin is required for height auto-resize.
 *     @type string $height     Fixed height (e.g. "900px"). Empty = auto-resize to content.
 *     @type string $max_width  Max width of the embed (default "720px"; "none" = full column).
 *     @type string $title      Accessible iframe title.
 *     @type string $caption    Optional caption shown beneath the widget.
 * }
 * @return string HTML.
 */
function bbw_render( $atts = array() ) {
	$atts = shortcode_atts(
		array(
			'src'       => '',
			'height'    => '',
			'max_width' => '720px',
			'title'     => "Balance Boulder's Budget — interactive",
			'caption'   => '',
		),
		$atts,
		'boulder_budget'
	);

	// Resolve the source URL.
	if ( '' !== trim( $atts['src'] ) ) {
		$url = esc_url( $atts['src'] );
	} else {
		list( $file_url, $ver ) = bbw_widget_source();
		if ( '' === $file_url ) {
			// Only bother an editor/admin with the diagnostic.
			if ( current_user_can( 'edit_posts' ) ) {
				return '<div style="padding:1rem;border:1px solid #CF2E2E;border-radius:6px;color:#CF2E2E;font:600 13px/1.5 system-ui,sans-serif">Boulder Budget Widget: the compiled widget file is missing. Build it with <code>BBW_PREVIEW=0 ./build-standalone.sh</code> and copy <code>boulder-budget-widget.html</code> into the plugin&rsquo;s <code>assets/</code> folder.</div>';
			}
			return '';
		}
		$url = esc_url( add_query_arg( 'v', $ver, $file_url ) );
	}

	$auto      = ( '' === trim( $atts['height'] ) );
	$height    = bbw_css_len( $atts['height'], '1200px' );
	$max_width = 'none' === strtolower( trim( $atts['max_width'] ) ) ? '100%' : bbw_css_len( $atts['max_width'], '720px' );
	$min_px    = $auto ? '600' : preg_replace( '/[^0-9]/', '', $height );
	$min_px    = '' === $min_px ? '600' : $min_px;

	$iframe_style = 'width:100%;border:0;display:block;background:#fff;'
		. ( $auto ? 'min-height:' . intval( $min_px ) . 'px;' : 'height:' . $height . ';' );

	// Load the front-end helpers only where the embed actually appears.
	wp_enqueue_style( 'boulder-budget-widget' );
	wp_enqueue_script( 'boulder-budget-widget' );

	ob_start();
	?>
	<div class="bbw-embed" style="max-width:<?php echo esc_attr( $max_width ); ?>;margin:1.5rem auto;">
		<iframe
			class="bbw-frame"
			src="<?php echo $url; /* escaped above via esc_url */ ?>"
			title="<?php echo esc_attr( $atts['title'] ); ?>"
			style="<?php echo esc_attr( $iframe_style ); ?>"
			loading="lazy"
			scrolling="<?php echo $auto ? 'no' : 'auto'; ?>"
			referrerpolicy="strict-origin-when-cross-origin"
			data-bbw-auto="<?php echo $auto ? '1' : '0'; ?>"
			data-bbw-min="<?php echo esc_attr( $min_px ); ?>"
		></iframe>
		<?php if ( '' !== trim( $atts['caption'] ) ) : ?>
			<figcaption class="bbw-caption"><?php echo esc_html( $atts['caption'] ); ?></figcaption>
		<?php endif; ?>
	</div>
	<?php
	return trim( ob_get_clean() );
}
add_shortcode( 'boulder_budget', 'bbw_render' );

/**
 * Register the dynamic Gutenberg block (metadata + attributes from block.json,
 * server-rendered through the same callback as the shortcode).
 */
function bbw_register_block() {
	if ( ! function_exists( 'register_block_type' ) ) {
		return; // Classic-only install; the shortcode still works.
	}
	register_block_type(
		BBW_PLUGIN_DIR,
		array( 'render_callback' => 'bbw_render_block' )
	);
}
add_action( 'init', 'bbw_register_block' );

/**
 * Map block attributes to the shared renderer.
 *
 * @param array $attributes Block attributes.
 * @return string
 */
function bbw_render_block( $attributes ) {
	$attributes = is_array( $attributes ) ? $attributes : array();
	return bbw_render(
		array(
			'src'       => isset( $attributes['src'] ) ? $attributes['src'] : '',
			'height'    => isset( $attributes['height'] ) ? $attributes['height'] : '',
			'max_width' => isset( $attributes['maxWidth'] ) ? $attributes['maxWidth'] : '720px',
			'title'     => isset( $attributes['title'] ) ? $attributes['title'] : "Balance Boulder's Budget — interactive",
			'caption'   => isset( $attributes['caption'] ) ? $attributes['caption'] : '',
		)
	);
}

/**
 * Enqueue the (build-free) editor script for the block, with its WP dependencies.
 */
function bbw_enqueue_block_editor() {
	wp_enqueue_script(
		'boulder-budget-widget-block',
		BBW_PLUGIN_URL . 'block.js',
		array( 'wp-blocks', 'wp-element', 'wp-block-editor', 'wp-components', 'wp-server-side-render' ),
		BBW_VERSION,
		true
	);
}
add_action( 'enqueue_block_editor_assets', 'bbw_enqueue_block_editor' );
