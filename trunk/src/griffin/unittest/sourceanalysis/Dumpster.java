package unittest.sourceanalysis;

import java.io.IOException;
import java.io.Writer;
import java.util.Iterator;
import java.util.NoSuchElementException;

import javax.swing.tree.DefaultMutableTreeNode;

import sourceanalysis.*;

/**
 * The Dumpster knows to create textual dumps of the program database.
 * These dumps are not reversible in the sense that one can rebuild the
 * original database from it, but at least they contain the <b>entire</b>
 * information in that way or another, so they can be used to make sure certain
 * data do end up in the database as they should.
 */
public class Dumpster {

	/**
	 * Constructor for Dumpster.
	 */
	public Dumpster() {
		super();
	}
	
	/**
	 * Writes name of an entity using the form:
	 * <p><tt>  entity1 of entity2 of </tt>...</p>
	 * Instead of using "::" as in C++.
	 * @param entity entity whose name to print
	 * @param out output stream
	 */
	public void dumpNameOf(Entity entity, Writer out) throws IOException
	{
		out.write("'");
		out.write(entity.getName());
		out.write("'");
		// Check if entity is contained
		ContainedConnection connection = entity.getContainer();
		if (connection != null) {
			out.write(" of ");
			dumpNameOf(connection.getContainer(), out);
		}
	}
	
	/**
	 * Dumps names of template arguments.
	 */
	public void dumpTemplateInformationOf(Entity entity, Writer out)
		throws IOException, MissingInformationException
	{
		if (entity.isTemplated()) {
			out.write(" (templated upon");			
			for (Iterator tpi = entity.templateParameterIterator(); tpi.hasNext(); ) {
				TemplateParameter tparam = (TemplateParameter)tpi.next();
				// Branch according to type of template paramter (typename/data)
				if (tparam instanceof TypenameTemplateParameter) {
					TypenameTemplateParameter ttp = (TypenameTemplateParameter)tparam;
					out.write(" typename "); out.write(ttp.getName());
					// Default value for data argument
					if (ttp.hasDefault()) {
						out.write(" [");
						dump(ttp.getDefault(), out);
						out.write("]");
					}					
				}
				else if (tparam instanceof DataTemplateParameter) {
					DataTemplateParameter dtp = (DataTemplateParameter)tparam;
					out.write(" ");
					dump(dtp.getType(), out);
					out.write(" "); out.write(dtp.getName());
					// Default value for data argument
					if (dtp.hasDefault()) {
						out.write(" [");
						out.write(dtp.getDefaultString());
						out.write("]");
					}
				}
			}
			out.write(")");
		}
	}
	
	/**
	 * Writes a visibility constant as a literal.
	 * @param vis a visibility constant taken from Specifiers.Visibility
	 * @param out output stream
	 */
	public void dumpVisibility(int vis, Writer out) throws IOException
	{
		if (vis == Specifiers.Visibility.PUBLIC) out.write(" public");
		else if (vis == Specifiers.Visibility.PROTECTED) out.write(" protected");
		else if (vis == Specifiers.Visibility.PRIVATE) out.write(" private");
	}
	
	/**
	 * Writes a storage constant.
	 * @param storage a storage constant taken from Specifiers.Storage
	 * @param out output stream
	 */
	public void dumpStorage(int storage, Writer out) throws IOException
	{
		if (storage == Specifiers.Storage.STATIC) out.write(" static");
	}
		
	/**
	 * Writes a virtuality constant.
	 * @param virt a virtuality constant taken from Specifiers.Virtuality
	 * @param out output stream
	 */
	public void dumpVirtuality(int virt, Writer out) throws IOException
	{
		if (virt == Specifiers.Virtuality.VIRTUAL) out.write(" virtual");
		else if (virt == Specifiers.Virtuality.PURE_VIRTUAL)
			out.write(" pure-virtual");
	}
		
	/**
	 * Create a dump of routine information.
	 * @param routine function to be dumped.
	 * @param out output stream
	 */
	public void dump(Routine routine, Writer out)
		throws IOException, MissingInformationException
	{
		out.write("[routine]");
		ContainedConnection connection = routine.getContainer();
		if (connection != null) {
			dumpVisibility(connection.getVisibility(), out);
			dumpStorage(connection.getStorage(), out);
			dumpVirtuality(connection.getVirtuality(), out);
		}
		out.write(" ");
		dumpNameOf(routine, out);
		dumpTemplateInformationOf(routine, out);
		// Dump const&inline
		if (routine.isConst()) out.write(" (const)");
		if (routine.isInline()) out.write(" (inline)");
		// Dump return type
		Type rtype = routine.getReturnType();
		if (rtype != null) {
			out.write(" returns ");
			dump((Type.TypeNode)rtype.getRoot(), out);
		}
		out.write("\n"); out.flush();
		// Dump parameters
		for (Iterator pi = routine.parameterIterator(); pi.hasNext(); ) {
			dump((Parameter)pi.next(), out);
		}
		// Dump grouping
		dumpGroupingOf(routine, out);
		dumpLocations(routine, out);
	}
	
	/**
	 * Dump information about a parameter.
	 * @param param parameter to be described
	 * @param out output stream
	 */
	public void dump(Parameter param, Writer out)
		throws IOException, MissingInformationException
	{
		out.write("[parameter] ");
		dumpNameOf(param, out);
		// Dump the type
		out.write(" has type ");
		dump((Type.TypeNode)param.getType().getRoot(), out);
		// Dump default value if any
		if (param.hasDefault()) {
			out.write(" defaults to ");
			out.write(param.getDefaultString());
		}
		out.write("\n"); out.flush();
	}
	
	/**
	 * Dump information about a field.
	 * @param field to be described
	 * @param out output stream
	 */
	public void dump(Field field, Writer out)
		throws IOException, MissingInformationException
	{
		out.write("[field]");
		ContainedConnection connection = field.getContainer();
		if (connection != null) {
			dumpVisibility(connection.getVisibility(), out);
			dumpStorage(connection.getStorage(), out);
		}
		out.write(" ");
		dumpNameOf(field, out);
		// Dump the type of the field
		out.write(" has type ");
		dump((Type.TypeNode)field.getType().getRoot(), out);
		// Dump initializer if any
		if (field.hasInitializer()) {
			out.write(" initialized as ");
			out.write(field.getInitializerString());
		}
		out.write("\n"); out.flush();
	}
	
	/**
	 * Dumps typedef (alias) information.
	 * @param alias alias to be described
	 * @param out output stream
	 */
	public void dump(Alias alias, Writer out)
		throws IOException, MissingInformationException
	{
		out.write("[alias] ");
		dumpNameOf(alias, out);
		// Dump the actual type
		out.write(" is an alias for ");
		dump(alias.getAliasedType(), out);
		out.write("\n"); out.flush();
	}
	
	/**
	 * Dumps enumerated type information.
	 * @param enume enumerated type to be described
	 * @param out output stream
	 */
	public void dump(sourceanalysis.Enum enume, Writer out)
		throws IOException
	{
		out.write("[enum] ");
		dumpNameOf(enume, out);
		out.write("\n");
		dumpLocations(enume, out);
		// Dump constants
		for (Iterator ci = enume.constantIterator(); ci.hasNext(); ) {
			sourceanalysis.Enum.Constant constant = (sourceanalysis.Enum.Constant)ci.next();
			out.write("[info] '");
			out.write(constant.getLiteral());
			out.write("' in ");
			dumpNameOf(enume, out);
			out.write(" is " + constant.getValue());
			out.write("\n");
		}
		out.flush();
	}
	
	/**
	 * Dump information contained in a namespace.
	 * @param namespace namespace to be dumped
	 * @param out output stream
	 */
	public void dump(Namespace namespace, Writer out)
		throws IOException, MissingInformationException
	{
		out.write("[namespace] ");
		dumpNameOf(namespace, out);
		out.write("\n"); out.flush();
		// Dump inner members
		dump(namespace.getScope(), out);
	}
	
	/**
	 * Dump information about an aggregate.
	 * @param aggregate class/struct/union entity to be dumped
	 * @param out output stream
	 */
	public void dump(Aggregate aggregate, Writer out)
		throws IOException, MissingInformationException
	{
		out.write("[class] ");
		dumpNameOf(aggregate, out);
		dumpTemplateInformationOf(aggregate, out);
		out.write("\n"); out.flush();
		dumpLocations(aggregate, out);
		// Dump base classes
		for (Iterator bi = aggregate.baseIterator(); bi.hasNext(); ) {
			InheritanceConnection connection = (InheritanceConnection)bi.next();
			out.write("[info] ");
			dumpNameOf(aggregate, out);
			out.write(" extends ");
			dumpNameOf(connection.getBase(), out);
			out.write(" as");
			dumpVisibility(connection.getVisibility(), out);
			out.write("\n"); out.flush();
		}
		// Dump inner members
		dump(aggregate.getScope(), out);
	}
	
	/**
	 * Dumps contents of a group scope. Only a summary of the items contained
	 * in the group (expressed by a list of their names) is actually dumped.
	 */
	public void dump(Group group, Writer out) throws IOException
	{
		out.write("[group] ");
		out.write(group.getName());
		out.write("\n");
	}
	
	/**
	 * Dumps contents of a scope.
	 * @param scope contained scope to be dumped
	 * @param out output stream
	 */
	public void dump(Scope scope, Writer out)
		throws IOException, MissingInformationException
	{
		// - dump routines
		for (Iterator ri = scope.routineIterator(); ri.hasNext(); ) {
			ContainedConnection connection = (ContainedConnection)ri.next();
			dump((Routine)connection.getContained(), out);
		}
		// - dump classes
		for (Iterator ci = scope.aggregateIterator(); ci.hasNext(); ) {
			ContainedConnection connection = (ContainedConnection)ci.next();
			dump((Aggregate)connection.getContained(), out);
		}
		// - dump namespaces
		for (Iterator ni = scope.namespaceIterator(); ni.hasNext(); ) {
			ContainedConnection connection = (ContainedConnection)ni.next();
			dump((Namespace)connection.getContained(), out);
		}
		// - dump field members
		for (Iterator fi = scope.fieldIterator(); fi.hasNext(); ) {
			ContainedConnection connection = (ContainedConnection)fi.next();
			dump((Field)connection.getContained(), out);
		}
		// - dump contained aliases
		for (Iterator ai = scope.aliasIterator(); ai.hasNext(); ) {
			ContainedConnection connection = (ContainedConnection)ai.next();
			dump((Alias)connection.getContained(), out);
		}
		// - dump enumerated types
		for (Iterator ei = scope.enumIterator(); ei.hasNext(); ) {
			ContainedConnection connection = (ContainedConnection)ei.next();
			dump((sourceanalysis.Enum)connection.getContained(), out);
		}
		out.flush();
	}

	/** 
	 * @param scope group scope
	 * @param out output stream
	 */
	public void dumpGroups(Scope scope, Writer out) throws IOException
	{
		// - dump contained groups
		for (Iterator gi = scope.groupIterator(); gi.hasNext(); ) {
			ContainedConnection connection = (ContainedConnection)gi.next();
			dump((Group)connection.getContained(), out);
		}
	}	

	/**
	 * Dumps the grouping information of an entity.
	 * @param entity a member entity which is (possibly) grouped
	 * @param out output stream
	 */
	public void dumpGroupingOf(Entity entity, Writer out) throws IOException
	{
		Group group = entity.getGroup();
		// Check if entity is grouped at all
		if (group != null) {
			out.write("[info] ");
			dumpNameOf(entity, out);
			out.write(" is grouped");
			while (group != null) {
				out.write(" in ");
				out.write(group.getName());
				// - go to higher-level group (if there is none, 'group'
				// will contain null as a result of this call)
				group = group.getGroup();
			}
			out.write("\n");
			out.flush();
		}
	}
	
	/**
	 * Dumps the location of the declaration/definition.
	 * @param entity observed entity
	 * @param out output stream
	 */
	public void dumpLocations(Entity entity, Writer out) throws IOException
	{
		SourceFile.DeclDefConnection connection = entity.getDeclaration();
		if (connection != null) {
			out.write("[info] ");
			dumpNameOf(entity, out);
			out.write(" is declared in ");
			try {
				out.write(connection.getSource().getName());
			}
			catch (MissingInformationException w) {
				out.write("*"); out.write(connection.getSourceFilename());
			}
			out.write(":" + connection.where().getStart().line);
			out.write("\n");
		}
	}

	/**
	 * Dumps a type node.
	 */
	public void dump(Type.TypeNode type, Writer out) throws IOException
	{
		if (type == null) {
			out.write("nothing");
			return ;
		}
		
		/* Branch upon kind of root node */
		try {
			switch (type.getKind()) {
			case Type.TypeNode.NODE_ARRAY:	/* array */
				out.write("array ");
				out.write(type.getChildAt(1).toString());
				out.write(" of ");
				dump((Type.TypeNode)type.getFirstChild(), out);
				break;
			case Type.TypeNode.NODE_FUNCTION:	/* function type */
				out.write("function returning ");
				dump((Type.TypeNode)type.getFirstChild(), out);
				break;
			case Type.TypeNode.NODE_POINTER:	/* pointer type */
				out.write("pointer to ");
				dump((Type.TypeNode)type.getFirstChild(), out);
				break;			
			case Type.TypeNode.NODE_REFERENCE:	/* reference type */
				out.write("reference to ");
				dump((Type.TypeNode)type.getFirstChild(), out);
				break;			
			case Type.TypeNode.NODE_TEMPLATE_INSTANTIATION:	/* template */
				out.write("instance of template ");
				dump((Type.TypeNode)type.getFirstChild(), out);
				// Dump the arguments of the template instance
				out.write(" with arguments");
				for (int i = 1; i < type.getChildCount(); ++i) {
					out.write(" ");
					// Fetch template argument from tree
					DefaultMutableTreeNode argumentNode =
						(DefaultMutableTreeNode)type.getChildAt(i);
					TemplateArgument argument =
						(TemplateArgument)argumentNode.getUserObject();
						
					if (argument instanceof TypenameTemplateArgument) {
						dump(((TypenameTemplateArgument)argument).getValue(), out);
					}
					else {
						out.write(argument.toString());
					}
				}
				break;
			case Type.TypeNode.NODE_LEAF: /* base type */
				try {
					dumpNameOf(type.getBase(), out);
				}
				catch (InappropriateKindException e) {
					out.write("<inapproperiate>");
				}
				break;
			}
		}
		catch (NoSuchElementException e) {
			out.write("<malformed>");
		}
	}
	
	/**
	 * Dumps a type (equivalent to dumping the root of the type).
	 * @param type type expression
	 * @param out output stream
	 */
	public void dump(Type type, Writer out) throws IOException
	{
		dump((Type.TypeNode)type.getRoot(), out);
	}

}
