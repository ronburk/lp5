<?xml version="1.0" encoding="UTF-8"?>
<!-- Validate one article against the schema enforced by tangle.xsl. -->
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

    <xsl:import href="tangle.xsl"/>
    <xsl:output method="text" encoding="UTF-8"/>

    <xsl:param name="article-location" select="'(input article)'"/>

    <xsl:template match="/">
        <xsl:call-template name="validate-article">
            <xsl:with-param name="document" select="."/>
            <xsl:with-param name="location" select="$article-location"/>
        </xsl:call-template>
        <xsl:text>Valid article: </xsl:text>
        <xsl:value-of select="$article-location"/>
        <xsl:text>&#10;</xsl:text>
    </xsl:template>
</xsl:stylesheet>
