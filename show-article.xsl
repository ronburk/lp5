<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

    <xsl:import href="tangle.xsl"/>
    <!-- Avoid inserting formatting whitespace into mixed content or code. -->
    <xsl:output method="xml" encoding="UTF-8" indent="no"
                omit-xml-declaration="no" cdata-section-elements="code"/>

    <xsl:param name="article-file" select="'lp5.lp5'"/>

    <xsl:template match="/">
        <xsl:call-template name="validate-article">
            <xsl:with-param name="document" select="."/>
            <xsl:with-param name="location" select="$article-file"/>
        </xsl:call-template>
        <lp5-article version="1" file="{$article-file}">
            <xsl:copy-of select="template"/>
        </lp5-article>
        <xsl:text>&#10;</xsl:text>
    </xsl:template>
</xsl:stylesheet>
