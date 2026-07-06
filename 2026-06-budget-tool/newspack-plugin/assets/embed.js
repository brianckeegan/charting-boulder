/**
 * Boulder Budget Widget — front-end embed helper.
 *
 * The widget ships as a self-contained HTML document rendered inside an iframe.
 * When that iframe is SAME-ORIGIN (the default: the file is served from this
 * plugin's own folder), the parent page can read the inner document's height and
 * size the iframe to it — no scrollbars, no fixed guess, and NO changes to the
 * widget build. A ResizeObserver keeps it correct as the reader expands the
 * survey, opens the sources panel, etc.
 *
 * If the iframe is cross-origin (a `src` override on another domain), the browser
 * blocks measurement; we fall back to the min-height and also listen for an
 * optional { type: 'bbw-height', height } postMessage in case a future build
 * emits one.
 */
( function () {
	'use strict';

	function fit( frame ) {
		if ( frame.getAttribute( 'data-bbw-auto' ) !== '1' ) {
			return;
		}
		var min = parseInt( frame.getAttribute( 'data-bbw-min' ), 10 ) || 600;
		try {
			var doc = frame.contentDocument || ( frame.contentWindow && frame.contentWindow.document );
			if ( ! doc || ! doc.documentElement ) {
				return;
			}
			var h = Math.max(
				doc.documentElement.scrollHeight,
				doc.body ? doc.body.scrollHeight : 0
			);
			frame.style.height = Math.max( h, min ) + 'px';
		} catch ( e ) {
			// Cross-origin: measurement is blocked. Keep a sensible min height.
			if ( ! frame.style.height ) {
				frame.style.height = min + 'px';
			}
		}
	}

	function wire( frame ) {
		var measure = function () { fit( frame ); };

		frame.addEventListener( 'load', function () {
			measure();
			// A couple of delayed passes catch late layout (web fonts, images).
			setTimeout( measure, 250 );
			setTimeout( measure, 1000 );

			try {
				var win = frame.contentWindow;
				var doc = frame.contentDocument;
				if ( doc && win && 'ResizeObserver' in win ) {
					var ro = new win.ResizeObserver( measure );
					ro.observe( doc.documentElement );
					if ( doc.body ) {
						ro.observe( doc.body );
					}
				}
				if ( win ) {
					win.addEventListener( 'resize', measure );
				}
			} catch ( e ) {
				// Cross-origin — nothing more we can observe.
			}
		} );

		// Re-fit when the parent column changes width (responsive breakpoints).
		window.addEventListener( 'resize', measure );
	}

	// Optional cross-origin fallback: a build that posts its own height.
	window.addEventListener( 'message', function ( ev ) {
		var d = ev.data;
		if ( ! d || d.type !== 'bbw-height' || typeof d.height !== 'number' ) {
			return;
		}
		var frames = document.querySelectorAll( 'iframe.bbw-frame' );
		for ( var i = 0; i < frames.length; i++ ) {
			if ( frames[ i ].contentWindow === ev.source ) {
				frames[ i ].style.height = Math.max( d.height, 300 ) + 'px';
			}
		}
	}, false );

	function init() {
		var frames = document.querySelectorAll( 'iframe.bbw-frame' );
		for ( var i = 0; i < frames.length; i++ ) {
			wire( frames[ i ] );
		}
	}

	if ( document.readyState === 'loading' ) {
		document.addEventListener( 'DOMContentLoaded', init );
	} else {
		init();
	}
} )();
