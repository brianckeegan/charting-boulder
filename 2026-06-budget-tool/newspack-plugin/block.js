/**
 * Editor UI for the "Boulder Budget Widget" block.
 *
 * Deliberately written in plain ES5 against the global `wp.*` packages so the
 * plugin needs NO build step (no @wordpress/scripts, no JSX compile). The block
 * is dynamic — it renders server-side via the same PHP callback as the
 * [boulder_budget] shortcode — so the editor just shows a live ServerSideRender
 * preview plus a settings panel.
 */
( function ( wp ) {
	'use strict';

	var el                = wp.element.createElement;
	var registerBlockType = wp.blocks.registerBlockType;
	var useBlockProps     = wp.blockEditor.useBlockProps;
	var InspectorControls = wp.blockEditor.InspectorControls;
	var PanelBody         = wp.components.PanelBody;
	var TextControl       = wp.components.TextControl;
	var ServerSideRender  = wp.serverSideRender;

	var BLOCK = 'charting-boulder/boulder-budget';

	function field( label, key, props, help ) {
		return el( TextControl, {
			label: label,
			value: props.attributes[ key ],
			help: help || null,
			onChange: function ( value ) {
				var next = {};
				next[ key ] = value;
				props.setAttributes( next );
			}
		} );
	}

	registerBlockType( BLOCK, {
		edit: function ( props ) {
			return el(
				'div',
				useBlockProps(),
				el(
					InspectorControls,
					{},
					el(
						PanelBody,
						{ title: 'Widget settings', initialOpen: true },
						field( 'Height (blank = auto-fit)', 'height', props, 'e.g. 900px. Leave blank to size to the content automatically.' ),
						field( 'Max width', 'maxWidth', props, 'e.g. 720px, or "none" for the full column.' ),
						field( 'Caption', 'caption', props ),
						field( 'Source URL override', 'src', props, 'Optional. Defaults to the bundled build. Use a same-origin URL for auto-fit.' )
					)
				),
				el( ServerSideRender, {
					block: BLOCK,
					attributes: props.attributes
				} )
			);
		},
		// Dynamic block: markup comes from PHP, so nothing is saved to post content.
		save: function () {
			return null;
		}
	} );
} )( window.wp );
