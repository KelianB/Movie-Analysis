$(document).ready(() => {
    // Handle navigation (hide previous panel and fade-in new)
    $(".sidebar .nav-link").click(function() {
        if(!$(this).attr("data-disabled") && !$(this).hasClass("active")) {
            // Hide previous section
            $(".sidebar .nav-link.active").removeClass("active");
            $(".content-div").hide();

            // Show new section
            $(this).addClass("active");
            let sectionDivId = $(this).attr("data-div");
            $("#" + sectionDivId).fadeIn();

            // Trigger listener for new section
            if(sectionShowListeners[sectionDivId])
                sectionShowListeners[sectionDivId]();
        }
    });

    let activeSection = $(".sidebar .nav-link.active");
    $("#" + activeSection.attr("data-div")).show();
});

function enableMovieSpecificSections() {
    $(".sidebar .nav-link[data-disabled]").removeAttr("data-disabled");
}