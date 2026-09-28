<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

    <xsl:output method="html" encoding="UTF-8" omit-xml-declaration="yes"/>

    <xsl:template match="/">
        <xsl:call-template name="emit-document">
            <xsl:with-param name="document" select="."/>
            <xsl:with-param name="root" select="."/>
        </xsl:call-template>
    </xsl:template>

    <xsl:template name="emit-document">
        <xsl:param name="document"/>
        <xsl:param name="root"/>

        <xsl:for-each select="$document/*/code[not(normalize-space(../name))]">
            <xsl:apply-templates select="node()" mode="emit-code">
                <xsl:with-param name="root" select="$root"/>
                <xsl:with-param name="stack" select="'|'"/>
            </xsl:apply-templates>
        </xsl:for-each>

        <xsl:for-each select="$document/*/children/li">
            <xsl:variable name="child" select="document(string(@id), .)"/>
            <xsl:call-template name="emit-document">
                <xsl:with-param name="document" select="$child"/>
                <xsl:with-param name="root" select="$root"/>
            </xsl:call-template>
        </xsl:for-each>
    </xsl:template>

    <xsl:template match="text()" mode="emit-code">
        <xsl:value-of select="." disable-output-escaping="yes"/>
    </xsl:template>

    <xsl:template match="*" mode="emit-code">
        <xsl:param name="root"/>
        <xsl:param name="stack"/>
        <xsl:choose>
            <xsl:when test="self::lp5-">
                <xsl:call-template name="emit-reference">
                    <xsl:with-param name="root" select="$root"/>
                    <xsl:with-param name="name" select="normalize-space(@ref)"/>
                    <xsl:with-param name="stack" select="$stack"/>
                </xsl:call-template>
            </xsl:when>
            <xsl:otherwise>
                <xsl:copy>
                    <xsl:apply-templates select="@*|node()" mode="emit-code">
                        <xsl:with-param name="root" select="$root"/>
                        <xsl:with-param name="stack" select="$stack"/>
                    </xsl:apply-templates>
                </xsl:copy>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <xsl:template match="@*" mode="emit-code">
        <xsl:copy/>
    </xsl:template>

    <xsl:template name="emit-reference">
        <xsl:param name="root"/>
        <xsl:param name="name"/>
        <xsl:param name="stack"/>

        <xsl:if test="not(string-length($name))">
            <xsl:message terminate="yes">A code reference has no name.</xsl:message>
        </xsl:if>
        <xsl:if test="contains($stack, concat('|', $name, '|'))">
            <xsl:message terminate="yes">
                <xsl:text>Circular code reference: </xsl:text>
                <xsl:value-of select="$name"/>
            </xsl:message>
        </xsl:if>

        <xsl:variable name="matches">
            <xsl:call-template name="count-named-fragments">
                <xsl:with-param name="document" select="$root"/>
                <xsl:with-param name="name" select="$name"/>
            </xsl:call-template>
        </xsl:variable>
        <xsl:if test="not(string-length(string($matches)))">
            <xsl:message terminate="yes">
                <xsl:text>No code fragment named '</xsl:text>
                <xsl:value-of select="$name"/>
                <xsl:text>'.</xsl:text>
            </xsl:message>
        </xsl:if>

        <xsl:call-template name="emit-named-fragments">
            <xsl:with-param name="document" select="$root"/>
            <xsl:with-param name="root" select="$root"/>
            <xsl:with-param name="name" select="$name"/>
            <xsl:with-param name="stack" select="concat($stack, $name, '|')"/>
        </xsl:call-template>
    </xsl:template>

    <xsl:template name="count-named-fragments">
        <xsl:param name="document"/>
        <xsl:param name="name"/>

        <xsl:for-each select="$document/*[normalize-space(string(name)) = $name]">
            <xsl:text>x</xsl:text>
        </xsl:for-each>
        <xsl:for-each select="$document/*/children/li">
            <xsl:variable name="child" select="document(string(@id), .)"/>
            <xsl:call-template name="count-named-fragments">
                <xsl:with-param name="document" select="$child"/>
                <xsl:with-param name="name" select="$name"/>
            </xsl:call-template>
        </xsl:for-each>
    </xsl:template>

    <xsl:template name="emit-named-fragments">
        <xsl:param name="document"/>
        <xsl:param name="root"/>
        <xsl:param name="name"/>
        <xsl:param name="stack"/>

        <xsl:for-each select="$document/*[normalize-space(string(name)) = $name]/code">
            <xsl:apply-templates select="node()" mode="emit-code">
                <xsl:with-param name="root" select="$root"/>
                <xsl:with-param name="stack" select="$stack"/>
            </xsl:apply-templates>
        </xsl:for-each>
        <xsl:for-each select="$document/*/children/li">
            <xsl:variable name="child" select="document(string(@id), .)"/>
            <xsl:call-template name="emit-named-fragments">
                <xsl:with-param name="document" select="$child"/>
                <xsl:with-param name="root" select="$root"/>
                <xsl:with-param name="name" select="$name"/>
                <xsl:with-param name="stack" select="$stack"/>
            </xsl:call-template>
        </xsl:for-each>
    </xsl:template>

</xsl:stylesheet>
